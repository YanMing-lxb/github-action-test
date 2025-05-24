
from logger_config import setup_logger
from htc import HTCCalculator
from air_properties import AirProperties
logger = setup_logger()

class UnitConverter:

    @staticmethod
    def convert(value, from_unit, to_unit, unit_type):
        conversions = {
            "length": {"m": 1.0, "cm": 0.01, "mm": 0.001}, 
            "temp": {"℃": lambda x: x, "K": lambda x: x - 273.15}, 
            "power": {"W": 1.0, "kW": 1000.0},
            "speed": {"km/h": lambda x: x, "m/s": lambda x: x * 1000 / 3600},
            "time": {"h": 1.0, "min": 1/60, "s": 1/3600}
        }

        if unit_type in ["temp", "speed"]:
            return conversions[unit_type][to_unit](value)
        return value * conversions[unit_type][from_unit] / conversions[unit_type][to_unit]

class HeatLoadCalculator:
    def __init__(self, inputs, page, message_show):
        self.inputs = inputs
        self.page = page
        self.message_show = message_show
        self.ap = AirProperties()
        

    def calculate_all(self, htc_advanced, precool):
        # 计算车厢尺寸（转换为米）
        length = UnitConverter.convert(self.inputs['length'], self.inputs['length_unit'], 'm', 'length')
        width  = UnitConverter.convert(self.inputs['width'], self.inputs['width_unit'], 'm', 'length')
        height  = UnitConverter.convert(self.inputs['height'], self.inputs['height_unit'], 'm', 'length')
        thickness = UnitConverter.convert(self.inputs['thickness'], self.inputs['thickness_unit'], 'm', 'length')

        # ------------------------------------------------------------
        # 计算几何参数
        # ------------------------------------------------------------
        # 箱体产热面积
        area_in, area_out = self._calculate_surface_areas(length, width, height, thickness)
        effective_area = (area_in * area_out) ** 0.5
        # 箱体体积
        internal_volume = self._calculate_internal_volume(length, width, height, thickness)

        # 获取温度参数
        T_env = UnitConverter.convert(self.inputs['env_temp'], self.inputs['env_temp_unit'], '℃', 'temp')
        T_chi = UnitConverter.convert(self.inputs['chi_temp'], self.inputs['chi_temp_unit'], '℃', 'temp')
        T_fro = UnitConverter.convert(self.inputs['fro_temp'], self.inputs['fro_temp_unit'], '℃', 'temp')
        T_fro_out = UnitConverter.convert(self.inputs['fro_out_temp'], self.inputs['fro_out_temp_unit'], '℃', 'temp')

        speed = UnitConverter.convert(self.inputs['speed'], self.inputs['speed_unit'], 'm/s', 'speed')
        
        htc_calculator = HTCCalculator(self.inputs, self.page, self.message_show, speed, T_env, UnitConverter)
        if htc_advanced:
            htc, T_suf = htc_calculator.get_htc()
        else:
            htc_conv_out = htc_calculator.calculate_external_convection(speed)
            T_suf = htc_calculator.calculate_external_temperature(htc_conv_out)
            htc = self.inputs['htc']
        # 车厢内外温差
        delta_T_chi = T_env - T_chi
        delta_T_fro = T_env - T_fro

        # ------------------------------------------------------------
        # 隔热车厢隔热壁热负荷计算
        # ------------------------------------------------------------
        Q_wall = {
            'fre': self._calculate_wall_heat(htc, effective_area, delta_T_chi),
            'frz': self._calculate_wall_heat(htc, effective_area, delta_T_fro)
        }

        # ------------------------------------------------------------
        # 隔热车厢漏热计算
        # ------------------------------------------------------------
        # 漏气量 kg/s 箱体体积m³×漏气倍数1/h×空气密度kg/m³ /3600
        m_leak = self._calculate_air_leakage(internal_volume)
        Q_leak = self._calculate_leak_heat(m_leak, T_env, T_chi, T_fro)

        # ------------------------------------------------------------
        # 太阳辐射热负荷计算
        # ------------------------------------------------------------
        Q_radiation = self._calculate_radiation_heat(htc, effective_area, T_env, T_suf)
        
        # ------------------------------------------------------------
        # 开关门热负荷
        # ------------------------------------------------------------
        Q_open = self._calculate_door_open_heat(internal_volume, T_env, delta_T_chi, delta_T_fro)
        
        # ------------------------------------------------------------
        # 装载货物热负荷
        # ------------------------------------------------------------
        Q_resp_chi = self._calculate_respiration_heat()
        Q_load_fro = self._calculate_chiezing_load(T_fro, T_fro_out)

        # ------------------------------------------------------------
        # 电气热负荷
        # ------------------------------------------------------------
        Q_electric = self._calculate_electric_heat()

        # ------------------------------------------------------------
        # 厢体预冷热负荷
        # ------------------------------------------------------------
        if precool:
            Q_cabin_precool = self._calculate_cabin_precool(effective_area, delta_T_chi, delta_T_fro)

        # ------------------------------------------------------------
        # 冷藏货物预冷热负荷
        # ------------------------------------------------------------
        Q_goods_precool_chi = self._calculate_goods_precool(delta_T_chi)

        # ------------------------------------------------------------
        # 最终负荷
        # ------------------------------------------------------------
        safety_coeff = self.inputs['safety_coeff'] # 安全系数

        if precool:
            Q_total = {
                'fre': (Q_wall['fre'] + Q_leak['fre'] + Q_radiation + Q_open['fre'] 
                    + Q_resp_chi + Q_electric + Q_cabin_precool['fre'] 
                    + Q_goods_precool_chi) * safety_coeff,
                'frz': (Q_wall['frz'] + Q_leak['frz'] + Q_radiation + Q_open['frz'] 
                    + Q_load_fro + Q_electric + Q_cabin_precool['frz']) * safety_coeff
            }
            return {
                'Q_electric': Q_electric,
                'Q_radiation': Q_radiation,

                'Q_wall_chi': Q_wall['fre'],
                'Q_leak_chi': Q_leak['fre'],
                'Q_open_chi': Q_open['fre'],
                'Q_resp_chi': Q_resp_chi,
                'Q_cabin_precool_chi': Q_cabin_precool['fre'],
                'Q_goods_precool_chi': Q_goods_precool_chi,
                'Q_total_chi': Q_total['fre'],
                'Q_total1_chi': Q_total['fre'],

                'Q_wall_fro': Q_wall['frz'],
                'Q_leak_fro': Q_leak['frz'],
                'Q_open_fro': Q_open['frz'],
                'Q_load_fro': Q_load_fro,
                'Q_cabin_precool_fro': Q_cabin_precool['frz'],
                'Q_total_fro': Q_total['frz'],
                'Q_total1_fro': Q_total['frz'],
            }
        else:
            Q_total = {
                'fre': (Q_wall['fre'] + Q_leak['fre'] + Q_radiation + Q_open['fre'] 
                    + Q_resp_chi + Q_electric) * safety_coeff,
                'frz': (Q_wall['frz'] + Q_leak['frz'] + Q_radiation + Q_open['frz'] 
                    + Q_load_fro + Q_electric) * safety_coeff
            }
            return {
                'Q_electric': Q_electric,
                'Q_radiation': Q_radiation,

                'Q_wall_chi': Q_wall['fre'],
                'Q_leak_chi': Q_leak['fre'],
                'Q_open_chi': Q_open['fre'],
                'Q_resp_chi': Q_resp_chi,
                'Q_total_chi': Q_total['fre'],
                'Q_total1_chi': Q_total['fre'],

                'Q_wall_fro': Q_wall['frz'],
                'Q_leak_fro': Q_leak['frz'],
                'Q_open_fro': Q_open['frz'],
                'Q_load_fro': Q_load_fro,
                'Q_total_fro': Q_total['frz'],
                'Q_total1_fro': Q_total['frz'],
            }

        
    
    def _calculate_internal_volume(self, l, w, h, t):
        """计算内部体积"""
        return (l-2*t) * (w-2*t) * (h-2*t)
    
    def _calculate_surface_areas(self, l, w, h, t):
        """计算内外表面积"""
        ai = 2*((l-2*t)*(w-2*t) + (l-2*t)*(h-2*t) + (w-2*t)*(h-2*t))
        ao = 2*(l*w + l*h + w*h)
        return ai, ao

    def _calculate_wall_heat(self, htc, area, delta_T):
        """计算壁面传热"""
        q = htc * area * delta_T
        return q

    def _calculate_air_leakage(self, volume):
        """计算空气泄漏量"""
        air_props = self.ap.dry(self.inputs['env_temp'])
        return self.inputs['leak_multiple'] * air_props['density'] * volume / 3600

    def _calculate_leak_heat(self, m_leak, T_env, T_chi, T_fro):
        """计算泄漏热负荷"""
        # 获取空气属性
        phi_chi = self.inputs['chi_relative_humidity']
        phi_fro = self.inputs['fro_relative_humidity']
        phi_env = self.inputs['env_relative_humidity']

        moist_env = self.ap.moist(T_env, phi_env)

        latent = 2500  # 水的汽化潜热 kJ/kg

        def calculate(m_leak, T_inn, phi_inn):
            air_dry = self.ap.dry(T_inn)
            delta_T = T_env - T_inn 
            moist_inn = self.ap.moist(T_inn, phi_inn)
            return m_leak * (
                air_dry['heat_capacity'] * delta_T +
                latent * (phi_env*moist_env['moisture_content'] - phi_inn*moist_inn['moisture_content'])
            )

        return {
            'fre': calculate(m_leak, T_chi, phi_chi),
            'frz': calculate(m_leak, T_fro, phi_fro)
        }

    def _calculate_radiation_heat(self, htc, area, T_env, T_suf):
        """计算太阳辐射热""" 
        ratio = self.inputs['radiation_area_ratio'] # 辐射面积 = 车箱面积×辐射面积系数 系数一般取 35%~50%
        radiation_area = area * ratio
        radiation_time = UnitConverter.convert(self.inputs['radiation_time'], self.inputs['radiation_time_unit'], 'h', 'time')
        time_ratio = radiation_time / 24 # 车厢受辐射时长 一般取 12~14 小时

        return htc * radiation_area * (T_suf - T_env) * time_ratio

    def _calculate_door_open_heat(self, volume, T_env, delta_T_chi, delta_T_fro):
        """计算开门热负荷"""
        air_props = self.ap.dry(T_env)
        # 开门质量流量,单位：kg/h，每次开门车厢放空，空气质量×次数/24 小时
        mass_flow = volume * air_props['density'] * self.inputs['open_close_frequency'] / 24
        cp = air_props['heat_capacity']

        return {
            'fre': mass_flow * cp * delta_T_chi / 3600,
            'frz': mass_flow * cp * delta_T_fro / 3600
        }

    def _calculate_respiration_heat(self):
        """计算货物呼吸热
        呼吸热=呼吸热系数×质量
        """
        return self.inputs['chi_resp_heat'] * self.inputs['chi_load_mass']

    def _calculate_chiezing_load(self, T_fro, T_fro_out):
        """计算冻结负荷"""
        return (self.inputs['fro_specific_heat'] *
                (T_fro_out - T_fro) *
                self.inputs['fro_load_mass'] * 1000 / 24 / 3600)

    def _calculate_electric_heat(self):
        """计算电气热负荷"""
        light_time = UnitConverter.convert(self.inputs['light_time'], self.inputs['light_time_unit'], 'h', 'time')
        fan_time = UnitConverter.convert(self.inputs['fan_time'], self.inputs['fan_time_unit'], 'h', 'time')

        return (self.inputs['light_power'] * light_time +
                self.inputs['fan_power'] * fan_time) / 24

    def _calculate_cabin_precool(self, area, delta_T_chi, delta_T_fro):
        """计算厢体预冷负荷"""
        wall_mass = self.get_wall_mass(
            self.inputs['density_walls'],
            self.inputs['thickness_walls'],
            area
        )
        avg_cp = self.get_average_specific_heat(
            self.inputs['density_walls'],
            self.inputs['specific_heat_walls'],
            self.inputs['thickness_walls']
        )
        cabin_precool_time = UnitConverter.convert(self.inputs['cabin_precool_time'], self.inputs['cabin_precool_time_unit'], 'h', 'time')

        return {
            'fre': wall_mass * avg_cp * delta_T_chi / (2 * cabin_precool_time),
            'frz': wall_mass * avg_cp * delta_T_fro / (2 * cabin_precool_time)
        }

    def _calculate_goods_precool(self, delta_T_chi):
        """计算货物预冷负荷"""
        cabin_precool_time = UnitConverter.convert(self.inputs['cabin_precool_time'], self.inputs['cabin_precool_time_unit'], 'h', 'time')
        return self.inputs['fro_specific_heat'] * self.inputs['chi_load_mass'] * delta_T_chi / cabin_precool_time


    def get_average_specific_heat(self, density_walls, specific_heat_walls, thickness_walls):
        """
        计算多层结构的平均比热容（单位：J/kg·K）
        """
        # 各层厢体材料密度，单位 kg/m³
        density_walls = list(map(float, str(density_walls).split()))
        # 各层厢体材料比热容，单位 J/kg·K
        specific_heat_walls = list(map(float, str(specific_heat_walls).split()))
        # 各层厢体材料厚度
        thickness_walls = [
            UnitConverter.convert(float(t_str), self.inputs['thickness_walls_unit'], 'm', 'length')
            for t_str in str(self.inputs['thickness_walls']).split()
        ]

        if not (len(density_walls) == len(specific_heat_walls) == len(thickness_walls)):
            logger.error(f"厢体各层参数的输入数量不一致（密度：{len(density_walls)}个值, 比热容：{len(specific_heat_walls)}, 厚度：{len(thickness_walls)}个值）")
            self.message_show(self.page, f"厢体各层参数的输入数量不一致（密度：{len(density_walls)}, 比热容：{len(specific_heat_walls)}个值, 厚度：{len(thickness_walls)}个值）", 'error')

        total_heat_capacity = 0.0 # 总热容（单位面积
        total_mass = 0.0          # 总质量（单位面积
        
        for density, specific_heat, thickness in zip(density_walls, specific_heat_walls, thickness_walls):
            if thickness <= 0:
                logger.error("厢体单层材料厚度必须大于零，请检查输入参数")
                self.message_show(self.page, "厢体单层材料厚度必须大于零，请检查输入参数", 'error')
            layer_mass = density * thickness
            total_heat_capacity += specific_heat * layer_mass
            total_mass += layer_mass

        if total_mass <= 0:
            logger.error("总质量必须大于零，请检查输入参数")
            self.message_show(self.page, "总质量必须大于零，请检查输入参数", 'error')

        return total_heat_capacity / total_mass

    def get_wall_mass(self, thickness_walls, density_walls, area):
        # 各层厢体材料密度，单位 kg/m³
        density_walls = list(map(float, str(density_walls).split()))
        # 各层厢体材料厚度
        thickness_walls = [
            UnitConverter.convert(float(t_str), self.inputs['thickness_walls_unit'], 'm', 'length')
            for t_str in str(self.inputs['thickness_walls']).split()
        ]
        # 检查输入列表长度一致性
        if len(thickness_walls) != len(density_walls):
            logger.error("厢体各层材料的导热率与密度的输入数值数量不一致")
            self.message_show(self.page, "厢体各层材料的导热率与密度的输入数值数量不一致", 'error')
        # 校验物理量合理性
        for d in thickness_walls:
            if d < 0:
                logger.error("厢体各层材料的厚度中不能存在负数")
                self.message_show(self.page, "厢体各层材料的厚度中不能存在负数", 'error')
        for rho in density_walls:
            if rho < 0:
                logger.error("厢体各层材料的密度中不能存在负数")
                self.message_show(self.page, "厢体各层材料的密度中不能存在负数", 'error')

        # 计算总质量（单位面积）
        total_mass = 0.0
        for d, rho in zip(thickness_walls, density_walls):
            total_mass += rho * d

        # 乘以总面积得到最终质量
        return total_mass * area




