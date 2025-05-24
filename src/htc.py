'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-04-08 15:22:10 +0800
LastEditTime : 2025-05-14 10:52:39 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /RefrTruck-HeatLoad-Solver/src/htc.py
Description  : 
 -----------------------------------------------------------------------
'''
from logger_config import setup_logger
logger = setup_logger()
import math
class HTCCalculator:
    def __init__(self, inputs, page, message_show, speed, T_env, UnitConverter):
        self.inputs = inputs
        self.page = page
        self.message_show = message_show
        self.speed = speed
        self.T_env = T_env
        self.UnitConverter = UnitConverter
        
    def get_htc(self) -> float:
        """综合计算车厢隔热壁传热系数"""
        # ------------------------------------------------------------
        # 输入参数校验
        # ------------------------------------------------------------
        self._validate_inputs()

        # ------------------------------------------------------------
        # 车厢隔热壁内部导热传热系数计算
        # ------------------------------------------------------------
        R_thermal = self._calculate_thermal_resistance()
        htc_cond = self._calculate_conductive_htc(R_thermal)

        # ------------------------------------------------------------
        # 车厢隔热壁外部对流传热系数计算
        # ------------------------------------------------------------
        htc_conv_out = self.calculate_external_convection(self.speed)

        # ------------------------------------------------------------
        # 车厢隔热壁内部对流传热系数计算
        # ------------------------------------------------------------
        htc_conv_in = self._calculate_internal_convection()

        # ------------------------------------------------------------
        # 车厢隔热壁外部辐射传热系数计算
        # ------------------------------------------------------------
        T_suf = self.calculate_external_temperature(htc_conv_out)
        htc_radiation = self._calculate_radiation_htc(T_suf)

        # ------------------------------------------------------------
        # 综合传热系数计算
        # ------------------------------------------------------------
        htc_total = self._calculate_total_htc(
            htc_cond, htc_conv_out + htc_radiation, htc_conv_in
        )
        
        # 热桥影响系数 根据热桥数量选定系数为1.1~1.25
        return htc_total * self.inputs['thermal_bridging_coeff'], T_suf

    def _validate_inputs(self):
        """校验所有输入参数的合法性"""
        thickness_walls = [
            self.UnitConverter.convert(float(t_str), self.inputs['thickness_walls_unit'], 'm', 'length')
            for t_str in str(self.inputs['thickness_walls']).split()
        ]
        thermal_conds = list(map(float, str(self.inputs['thermal_cond_walls']).split()))
        
        if len(thickness_walls) == 1 and thickness_walls[0] != self.UnitConverter.convert(float(self.inputs['thickness']), self.inputs['thickness_unit'], 'm', 'length'):
            logger.error(f"各层厚度输入单个数值时，应当与整体参数中的厢体厚度的值一致")
            self.message_show(self.page, f"各层厚度输入单个数值时，应当与整体参数中的厢体厚度的值一致）", 'error')
        if len(thickness_walls) != len(thermal_conds):
            logger.error(f"厢体各层参数的输入数量不一致（导热率：{len(thermal_conds)}, 厚度：{len(thickness_walls)}个值）")
            self.message_show(self.page, f"厢体各层参数的输入数量不一致（导热率：{len(thermal_conds)}, 厚度：{len(thickness_walls)}个值）", 'error')
        if any(d <= 0 for d in thickness_walls):
            logger.error("厢体各层材料的厚度中不能存在负数")
            self.message_show(self.page, "厢体各层材料的厚度中不能存在负数", 'error')
        if any(l <= 0 for l in thermal_conds):
            logger.error("厢体各层材料的导热系数中不能存在负数")
            self.message_show(self.page, "厢体各层材料的导热系数中不能存在负数", 'error')
        if not (2.0 <= self.inputs['beta'] <= 2.8):
            logger.error("对流系数β应在2.0~2.8范围内")
            self.message_show(self.page, "对流系数β应在2.0~2.8范围内", 'error')
        if self.inputs['solar_radiation'] < 0:
            logger.error("太阳辐射值不能为负")
            self.message_show(self.page, "太阳辐射值不能为负", 'error')

    def _calculate_thermal_resistance(self) -> float:
        """计算热阻"""
        # 各层厢体材料厚度 单位 m
        thickness_walls = [
            self.UnitConverter.convert(float(t_str), self.inputs['thickness_walls_unit'], 'm', 'length')
            for t_str in str(self.inputs['thickness_walls']).split()
        ]
        # 各层厢体材料导热系数 单位：W/m2K
        thermal_conds = list(map(float, str(self.inputs['thermal_cond_walls']).split()))
        return sum(d / l for d, l in zip(thickness_walls, thermal_conds))

    def _calculate_conductive_htc(self, R_thermal: float) -> float:
        """计算导热传热系数"""
        if R_thermal < 1e-9:  # 防止除零错误
            logger.error("总热阻值过小，可能导致计算溢出")
            self.message_show(self.page, "总热阻值过小，可能导致计算溢出", 'warning')
        return 1 / R_thermal

    def calculate_external_convection(self, speed: float) -> float:
        """计算外部对流传热系数"""
        return 6.31 * speed**0.656 + 3.25 * math.exp(-1.91 * speed)

    def calculate_external_temperature(self, htc_conv_out):
        solar = self.inputs['solar_radiation']
        alpha = self.inputs['surface_absorptivity'] 
        sigma = 0.0000000567
        epsilon  = self.inputs['surface_emissivity']
        T0 = self.T_env+273.15
        # 定义方程和导数
        def f(T):
            return epsilon  * sigma  * T**4 + htc_conv_out * T - (epsilon  * sigma  * T0**4 + htc_conv_out * T0 + alpha * solar)

        def df(T):
            return 4 * epsilon  * sigma * T**3 + htc_conv_out
        
        # 牛顿迭代
        T_initial = T0 + 20
        tolerance = 0.001
        max_iter = 500
        T = T_initial
        for _ in range(max_iter):
            F = f(T)
            dF = df(T)
            T_new = T - F / dF
            if abs(F) < tolerance:
                break
            T = T_new
        T = T -273.15

        logger.info(f"牛顿拉夫逊迭代求解辐射表面温度为 {T:.2f} °C，残差为 {abs(F):.6f}")
        self.message_show(self.page, f"牛顿拉夫逊迭代求解辐射表面温度为 {T:.2f} °C，残差为 {abs(F):.6f}", 'info')

        return T

    def _calculate_internal_convection(self) -> float:
        """计算内部对流传热系数"""
        ΔT_insuf = self.inputs['diff_insuf_with_inair']
        β = self.inputs['beta'] # 与厢内空气流动和温差有关的系数，在自然循环时2.3~2.8
    
        return 3 + 0.08 * ΔT_insuf if ΔT_insuf < 5 else β * ΔT_insuf**0.25

    def _calculate_radiation_htc(self, T_suf) -> float:
        """计算辐射传热系数"""
        # 太阳辐射
        solar = self.inputs['solar_radiation']
        # 表面吸收率
        absorptivity = self.inputs['surface_absorptivity'] 
        return solar * absorptivity / T_suf  # 隔热壁外表面与环境温差为20K

    def _calculate_total_htc(self, *htcs: float) -> float:
        """综合各传热系数"""
        total_htc = 1 / sum(1/h for h in htcs)
        if total_htc < 0.4:
            logger.info(f"综合传热系数为{total_htc} W/m²·℃，满足GB/T 29753高级隔热性能要求")
            self.message_show(self.page, f"综合传热系数为{total_htc:.2f} W/m²·℃，满足GB/T 29753高级隔热性能要求", 'info')
        elif total_htc < 0.7:
            logger.info(f"综合传热系数为{total_htc} W/m²·℃，满足GB/T 29753普通隔热性能要求")
            self.message_show(self.page, f"综合传热系数为{total_htc:.2f} W/m²·℃，满足GB/T 29753普通隔热性能要求", 'info')
        else:
            logger.warning(f"综合传热系数为{total_htc} W/m²·℃，不满足GB/T 29753规定的隔热性能要求")
            self.message_show(self.page, f"综合传热系数为{total_htc:.2f} W/m²·℃，不满足GB/T 29753规定的隔热性能要求", 'warning')
        return total_htc