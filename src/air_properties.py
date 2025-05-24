import math
from logger_config import setup_logger

logger = setup_logger()
class AirProperties():
    def __init__(self):
        pass

    def moist(self, T, phi):
        p_atm = 101325  # 单位 Pa
        
        Tk = T + 273.15 # 单位 K

        if Tk <= 0:
            logger.error("温度值无效，绝对温度需大于 0K")

        # Hyland-Wexler 公式 计算饱和水蒸气压 p_satu
        if T < 0: # 在温度-100~0℃范围内（标准大气压），饱和水蒸气的饱和压力计算。单位 Pa
            term1 = -5674.5359 / Tk
            term2 = 6.3925247
            term3 = -0.009677843 * Tk
            term4 = 6.2215701e-7 * Tk**2
            term5 = 2.0747825e-9 * Tk**3
            term6 = -9.484024e-13 * Tk**4
            term7 = 4.1635019 * math.log(Tk)
            p_satu = math.exp(term1 + term2 + term3 + term4 + term5 + term6 + term7)
        else: # 在温度0~200℃范围内（标准大气压），饱和水蒸气的饱和压力计算公式
            term1 = -5800.2206 / Tk
            term2 = 1.3914993
            term3 = -0.048640239 * Tk
            term4 = 4.1764768e-5 * Tk**2
            term5 = -1.4452093e-8 * Tk**3
            term6 = 6.5459673 * math.log(Tk)
            p_satu = math.exp(term1 + term2 + term3 + term4 + term5 + term6)
        
        # 水蒸气分压力 = 水蒸气饱和分压力 * 相对湿度
        p_water_vap = p_satu * phi
        if p_water_vap >= p_atm:
            logger.error(f"水蒸气压 {p_water_vap} Pa 超过大气压 {p_atm} Pa")

        # 含湿量，单位 kg/kg
        moisture_content = 0.621945 * p_water_vap / (p_atm - p_water_vap)

        # 计算露点温度
        if T >= 0 and T < 93:
            log_p = math.log(p_water_vap)
            T_dewpoint = 6.54 + 14.526 * log_p + 0.7389 * log_p**2 + 0.09486 * log_p**3 + 0.4569 * (p_water_vap**0.1984)
        elif T < 0:
            log_p = math.log(p_water_vap)
            T_dewpoint = 6.09 + 12.608 * log_p + 0.4959 * log_p**2
        else:
            logger.error(f"温度 {T}°C 超出露点公式适用范围")

        # 获取干空气物性参数
        dry_properties = self.dry(T)

        # 湿空气密度，单位 kg/m³
        density = dry_properties['density'] * (1 + moisture_content) / (461 * Tk * (0.622 + moisture_content))
        
        L = 2501000  # 蒸发潜热 (J/kg)
        c_pv = 1860   # 水蒸气定压比热容 (J/(kg·K))

        # 湿空气比焓 h 单位 j/kg
        enthalpy = (dry_properties['heat_capacity'] * T) + (moisture_content * (L + c_pv * T))

        return {
            'p_water_vap': p_water_vap,
            'moisture_content': moisture_content,
            'T_dewpoint': T_dewpoint,
            'density': density,
            'enthalpy': enthalpy
        }
    
    def dry(self, T):
        # 系数定义（按霍纳法则排序）
        DENSITY_COEFFS = [
            9.779381204240007e-16,
            -1.044387334699978e-12,
            4.058276919737977e-10,
            -7.793160257006469e-08,
            1.394452090867944e-05,
            -0.004253950660426637,
            1.2825222223126087
        ]
        THERM_COND_COEFFS = [
            -2.3572115917107644e-13,
            1.3446703357265586e-10,
            -3.34023615477079e-08,
            7.51588447776211e-05,
            0.02415885444726379
        ]
        KINEMATIC_VISC_COEFFS = [
            -4.8623014385789635e-14,
            1.1106612398551261e-10,
            8.616037812993472e-08,
            1.3388608811431725e-05
        ]
        DYNAMIC_VISC_COEFFS = [
            3.121881021638468e-14,
            -4.0747762815088714e-11,
            5.0261032795989934e-08,
            1.7209405690807253e-05
        ]
        HEAT_CAPACITY_COEFFS = [
            9.644494938773155e-15,
            -7.996769026471137e-12,
            -1.3098407581498805e-09,
            3.6264765598416506e-06,
            -0.0016216909506396135,
            0.3333034613775682,
            -33.083287512903205,
            2289.176881933999
        ]

        # 密度计算（霍纳法则） 单位 kg/m³
        density = 0.0
        for coeff in DENSITY_COEFFS:
            density = density * T + coeff

        # 比热容分段计算 单位 J/kg·K
        if T <= -150:
            heat_capacity = 1026
        elif -150 < T <= -100:
            heat_capacity = 1009 + 17*(T + 150)/50
        elif -100 < T <= -50:
            heat_capacity = 1005 + 4*(T + 100)/50
        elif -50 < T <= 40:
            heat_capacity = 1005
        elif 40 < T <= 60:
            heat_capacity = 1005 + 4*(T - 40)/20
        elif 60 < T <= 100:
            heat_capacity = 1009
        elif 100 < T <= 120:
            heat_capacity = 1009 + 4*(T - 100)/20
        elif 120 < T <= 140:
            heat_capacity = 1013
        else:
            heat_capacity = 0.0
            for coeff in HEAT_CAPACITY_COEFFS:
                heat_capacity = heat_capacity * T + coeff

        # 导热率计算 单位 W/m·K
        thermal_conductivity = 0.0
        for coeff in THERM_COND_COEFFS:
            thermal_conductivity = thermal_conductivity * T + coeff

        # 运动粘度计算 单位 m²/s
        kinematic_viscosity = 0.0
        for coeff in KINEMATIC_VISC_COEFFS:
            kinematic_viscosity = kinematic_viscosity * T + coeff

        # 动力粘度计算 单位 Pa·s
        dynamic_viscosity = 0.0
        for coeff in DYNAMIC_VISC_COEFFS:
            dynamic_viscosity = dynamic_viscosity * T + coeff

        return {
            'density': density,
            'heat_capacity': heat_capacity,
            'therm_cond': thermal_conductivity,
            'kinematic_viscosity': kinematic_viscosity,
            'Dynamic_viscosity': dynamic_viscosity
        }


