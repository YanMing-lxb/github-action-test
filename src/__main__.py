import os
import sys
import flet as ft
from bisect import bisect_left

from core import HeatLoadCalculator as HLC
from logger_config import setup_logger
from typing import Optional, Callable
from load_configuration import load_config
from product_recommender import update_recommendations
from version import __version__, __date__, __project_name__, __team__, __author__
logger = setup_logger()

# 在 main() 外部定义消息队列和锁
message_queue = []
priority_order = {"error": 0, "warning": 1, "info": 2, "success": 3}
config = load_config("config.toml")
product_info = load_config("product_config.toml")

# 按需提取数据
default_length = config["default_length"]
default_width = config["default_width"]
default_height = config["default_height"]
default_env_temp = config["default_env_temp"]
default_chi_temp = config["default_chi_temp"]
default_fro_temp = config["default_fro_temp"]
default_fro_out_temp = config["default_fro_out_temp"]
solar_radiation_prevalues = config["solar_radiation_prevalues"]
surface_absorptivity_prevalues = config["surface_absorptivity_prevalues"]
surface_emissivity_prevalues = config["surface_emissivity_prevalues"]
frozen_goods_prevalues = config["frozen_goods_prevalues"]
chilled_goods_prevalues = config["chilled_goods_prevalues"]


def main(page: ft.Page):
    def message_show(page, msg: str, msg_type: str = "error"):
        """优化后的消息提示方法
        :param msg: 要显示的消息内容
        :param msg_type: 消息类型(error/success/warning/info)，默认error
        """
        color_map = {
            "error": ft.Colors.RED_700,
            "success": ft.Colors.GREEN_700,
            "warning": ft.Colors.ORANGE_700,
            "info": ft.Colors.BLUE_700  # 新增 info 类型颜色
        }
        
        snack_bar = ft.SnackBar(
            elevation=8,
            bgcolor=color_map.get(msg_type, ft.Colors.RED_700),
            content=ft.Row([
                ft.Icon(
                    name=ft.Icons.ERROR if msg_type == "error" 
                        else ft.Icons.CHECK_CIRCLE if msg_type == "success" 
                        else ft.Icons.WARNING if msg_type == "warning"
                        else ft.Icons.INFO,  # 新增 info 图标
                    color=ft.Colors.WHITE
                ),
                ft.Text(msg, color=ft.Colors.WHITE, size=14)
            ], spacing=10),
            action="关闭",
            action_color=ft.Colors.WHITE,
            duration=6000,
            padding=ft.padding.symmetric(vertical=15, horizontal=20),
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        page.open(snack_bar)

        # 如果是 error 类型，则抛出异常中断执行
        if msg_type == "error":
            raise ValueError(f"Error occurred: {msg}")  # 抛出异常以中断执行

    def resource_path(assets_filename):
        """ 获取打包后或开发模式下的资源路径 """
        if getattr(sys, 'frozen', False):  # 打包后
            base_path = sys._MEIPASS
            assets_path = os.path.join(base_path, "assets", assets_filename)
        else:  # 开发模式下，基于 __main__.py 的位置向上找根目录
            base_path = os.path.abspath(".")
            assets_path = os.path.join(base_path, "src", "assets", assets_filename)
        return assets_path
        
    # ------------------------------------------------------------
    # 工具函数
    # ------------------------------------------------------------
    def create_dropdown_row(label, text_kwargs=None, unit_options=None, default_unit=None, unit_width=100, row_kwargs=None, tooltip=None):
        text_kwargs = text_kwargs or {}
        row_kwargs = row_kwargs or {}
        text_field = ft.TextField(label=label, **text_kwargs)
        if tooltip:
            text_field.tooltip = tooltip
        unit_dropdown = ft.Dropdown(width=unit_width, options=[ft.dropdown.Option(u) for u in unit_options], value=default_unit)
        row = ft.Row([text_field, unit_dropdown], **row_kwargs)
        return text_field, unit_dropdown, row

    def create_two_dropdown_row(label:str, dd_label: str=None, preset_options:list=None, connect_update: Optional[Callable] = None, text_kwargs:dict=None, unit_options:dict=None, default_unit:str=None, unit_width:int=100, row_kwargs:dict=None, tooltip:str=None)->tuple:
        text_kwargs = text_kwargs or {}
        row_kwargs = row_kwargs or {}

        # TODO 更改单位的同时更改选项中的数值
        # 提取默认值并从 text_kwargs 移除 'value'，防止冲突
        if 'value' in text_kwargs:
            default_value = text_kwargs.pop('value')
        else:
            default_value = preset_options[0]

        text_field = ft.TextField(label=label, value=default_value, width=100, **text_kwargs)
        def dropdown_changed(e):
            if connect_update:
                connect_update(text_dropdown.value)
            text_field.value = text_dropdown.value
            page.update()
        
        auto_menu_height = 240 if len(preset_options) > 6 else None

        text_dropdown = ft.Dropdown(
            label=dd_label, 
            # editable=editable, 
            width=140,
            menu_height = auto_menu_height, 
            options=[ft.dropdown.Option(u) for u in preset_options], 
            on_change=dropdown_changed, 
            # **text_kwargs
            )

        if tooltip:
            text_dropdown.tooltip = tooltip
        unit_dropdown = ft.Dropdown(width=unit_width, options=[ft.dropdown.Option(u) for u in unit_options], value=default_unit)
        row = ft.Row([text_field, unit_dropdown, text_dropdown], **row_kwargs)
        return text_field, unit_dropdown, row

    def create_text_unit_row(label, unit_text, text_kwargs=None, row_kwargs=None, tooltip=None):
        text_kwargs = text_kwargs or {}
        row_kwargs = row_kwargs or {}
        text_field = ft.TextField(label=label, **text_kwargs)
        if tooltip:
            text_field.tooltip = tooltip
        unit_widget = ft.Text(unit_text, weight=200, width=80)
        row = ft.Row([text_field, unit_widget], **row_kwargs)
        return text_field, unit_widget, row

    def create_dropdown_values_row(label, dd_label, unit_text, preset_options, row_kwargs=None, tooltip=None):

        row_kwargs = row_kwargs or {}

        default_value = next(iter(preset_options.keys()))

        text_field = ft.TextField(label=label, value=preset_options[default_value], width=100)

        def get_options():
            options = []
            for key in preset_options.keys():
                options.append(ft.DropdownOption(key=key))
            return options

        def dropdown_changed(e):
            text_field.value = preset_options[dropdown.value]
            page.update()
        
        dropdown = ft.Dropdown(
            label=dd_label,
            menu_height = 240, 
            width = 140, 
            options=get_options(),
            on_change=dropdown_changed,
        )

        if tooltip:
            dropdown.tooltip = tooltip

        # 创建 Text 组件显示单位
        unit_widget = ft.Text(unit_text, weight=200, width=80)

        # 将组件添加到 Row
        row = ft.Row([text_field, unit_widget, dropdown], **row_kwargs)

        return text_field, row
    
    def connect_update_wh(input_value):
        width.value = default_width.get(str(input_value))
        height.value = default_height.get(str(input_value))

    # ------------------------------------------------------------
    # 尺寸参数控件组
    # ------------------------------------------------------------
    length, length_unit, length_row = create_two_dropdown_row(label="长度", dd_label="常用尺寸", preset_options=default_length, connect_update=connect_update_wh, unit_options=["m", "cm", "mm"], default_unit="m")

    width, width_unit, width_row = create_dropdown_row(label="宽度", text_kwargs={"width": 100, 'value': default_width[str(default_length[0])]}, unit_options=["m", "cm", "mm"], default_unit="m", row_kwargs={"visible": False})

    height, height_unit, height_row = create_dropdown_row(label="高度", text_kwargs={"width": 100, 'value': default_height[str(default_length[0])]}, unit_options=["m", "cm", "mm"], default_unit="m", row_kwargs={"visible": False})

    thickness, thickness_unit, thickness_row = create_dropdown_row(label="箱体厚度", text_kwargs={"width": 100, "value":8}, unit_options=["m", "cm", "mm"], default_unit="cm", row_kwargs={"visible": False})

    # ------------------------------------------------------------
    # 换热参数控件组
    # ------------------------------------------------------------

    thermal_bridging_coeff, _, thermal_bridging_coeff_row = create_text_unit_row(label="热桥系数", unit_text="", text_kwargs={"width": 100, "value": 1.25}, tooltip="用于考虑厢体结构热桥效应，建议取值范围为 1.1~1.25", row_kwargs={"visible": False})

    htc, _, htc_row = create_text_unit_row(label="车厢导热系数", unit_text="  W/m²·℃", text_kwargs={"width": 100, "value": 0.4}, tooltip="车厢整体导热系数（GB/T 29753: 高级隔热 K≤0.4 W/m²·℃，普通隔热 0.4＜K≤0.7 W/m²·℃）")

    beta, _, beta_row = create_text_unit_row(label="对流系数", unit_text="", text_kwargs={"width": 100, "value": 2.5}, tooltip="与厢内空气流动和温差有关的对流系数，自然循环时推荐取值 2.3~2.8", row_kwargs={"visible": False})

    diff_insuf_with_inair, _, diff_insuf_with_inair_row = create_text_unit_row(label="厢内面气温差", unit_text="", text_kwargs={"width": 100, "value": 2}, tooltip="内部表面温度与内部空气温差，用于计算内部自然对流传热系数", row_kwargs={"visible": False})


    # ------------------------------------------------------------
    # 箱体参数控件组
    # ------------------------------------------------------------
    cabin_parameters_show = ft.Text("厢体参数", weight=ft.FontWeight.BOLD, size=18, visible=False)

    # 密度参数
    density_walls, _, density_walls_row = create_text_unit_row(label="厢体各层密度", unit_text="  kg/m³", text_kwargs={"width": 150, "value": "245 25 245"}, tooltip="厢体各层材料密度（支持多层或单层输入，如纤维板-聚苯乙烯泡沫-纤维板 则输入 245 25 245）", row_kwargs={"visible": False})

    # 比热容参数
    specific_heat_walls, _, specific_heat_walls_row = create_text_unit_row(label="厢体各层比热容", unit_text="  J/kg·K", text_kwargs={"width": 150, "value": "0"}, tooltip="厢体各层材料比热容（支持多层或单层输入）", row_kwargs={"visible": False})

    # 导热率参数
    thermal_cond_walls, _, thermal_cond_walls_row = create_text_unit_row(label="厢体各层导热率", unit_text="  W/(m·K)", text_kwargs={"width": 150, "value": "0.048 0.044 0.048"}, tooltip="厢体各层材料导热率（支持多层或单层输入，如纤维板-聚苯乙烯泡沫-纤维板 则输入 0.048 0.044 0.048）", row_kwargs={"visible": False})

    # 厚度参数
    thickness_walls, thickness_walls_unit, thickness_walls_row = create_dropdown_row(label="箱体各层厚度", text_kwargs={"width": 150, "value": "0.5 7 0.5", "tooltip": "请输入厢体各层材料厚度（支持多层或单层输入）"}, unit_options=["m", "cm", "mm"], default_unit="cm", row_kwargs={"visible": False})

    # ------------------------------------------------------------
    # 漏气倍数控件组
    # ------------------------------------------------------------
    leak_multiple, _, leak_multiple_row = create_text_unit_row(label="漏气倍数", unit_text="  1/h", text_kwargs={"width": 100, "value": 0.3}, row_kwargs={"visible": False}, tooltip="GB/T 29753: Area≤20㎡ L≤6.3，20㎡≤Area≤40㎡ L≤3.8，Area≥40㎡ L≤3")

    # 车速参数
    speed, speed_unit, speed_row = create_dropdown_row(label="车速", text_kwargs={"width": 100, "value": 60, "tooltip": "行驶平均速度，用于太阳辐射计算，默认值为 60 km/h。"}, unit_options=["km/h", "m/s"], default_unit="km/h", row_kwargs={"visible": False})


    # 冷藏车示意图
    RefrTruck_Schematic = ft.Image(width=350, fit=ft.ImageFit.CONTAIN, visible=True)
    RefrTruck_Schematic_Text = ft.Text("冷藏车示意图", weight=ft.FontWeight.BOLD, size=18, visible=True)
    # 布局列定义
    cpc_col1 = ft.Column([
        ft.Text("整体参数", weight=ft.FontWeight.BOLD, size=18),
        ft.Container(
            content=ft.Column([
                length_row,
                width_row,
                height_row,
                thickness_row,
                speed_row,
                leak_multiple_row,
                htc_row, 
                thermal_bridging_coeff_row, 
                beta_row, 
                diff_insuf_with_inair_row
            ], scroll=ft.ScrollMode.AUTO),
            expand=True
        )
    ])

    cpc_col2 = ft.Column([
        cabin_parameters_show,
        density_walls_row,
        specific_heat_walls_row,
        thermal_cond_walls_row,
        thickness_walls_row,
        RefrTruck_Schematic_Text,
        RefrTruck_Schematic,
    ])


    carriage_parameter = ft.Row(controls=[cpc_col1, cpc_col2], spacing=20, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
    carriage_parameter_controls = ft.Container(content=carriage_parameter, expand=True, padding=20)

    # 温度参数控件组
    env_temp, env_temp_unit, env_temp_row = create_two_dropdown_row(label="环境温度", dd_label="常用数值", preset_options=default_env_temp, text_kwargs={"value": 30}, unit_options=["℃", "K"], default_unit="℃", unit_width=85)
    chi_temp, chi_temp_unit, chi_temp_row = create_two_dropdown_row(label="冷藏温度", dd_label="常用数值", preset_options=default_chi_temp, text_kwargs={"value": 0}, unit_options=["℃", "K"], default_unit="℃", unit_width=85)
    fro_temp, fro_temp_unit, fro_temp_row = create_two_dropdown_row(label="冷冻温度", dd_label="常用数值", preset_options=default_fro_temp, text_kwargs={"value": -20}, unit_options=["℃", "K"], default_unit="℃", unit_width=85)


    # 湿度参数
    chi_relative_humidity = ft.TextField(label="冷藏相对湿度", width=100, value=0.5, visible=False , tooltip="冷藏时车厢内空气相对湿度，默认值为 0.5")
    fro_relative_humidity = ft.TextField(label="冷冻相对湿度", width=100, value=0.5, visible=False , tooltip="冷冻时车厢内空气相对湿度，默认值为 0.5")
    env_relative_humidity = ft.TextField(label="环境相对湿度", width=100, value=0.5, visible=False , tooltip="环境空气相对湿度，默认值为 0.5")
    
    
    solar_radiation, solar_radiation_row = create_dropdown_values_row(label="太阳辐照强度", dd_label="常用数值", unit_text="  W/m²", preset_options=solar_radiation_prevalues, tooltip="太阳辐射强度，默认值依据 QX/T 368—2016 标准设定为 1366.1 W/m²")

    surface_absorptivity, surface_absorptivity_row = create_dropdown_values_row(label="车厢吸收率", dd_label="常用数值", unit_text=" ", preset_options=surface_absorptivity_prevalues, tooltip="车厢表面吸收率，默认值为 0.35（白色涂漆）")

    surface_emissivity, surface_emissivity_row = create_dropdown_values_row(label="车厢发散率", dd_label="常用数值", unit_text=" ", preset_options=surface_emissivity_prevalues, tooltip="车厢表面发射率，默认值为 0.8")


    # 辐射参数
    radiation_area_ratio = ft.TextField(label="辐射面积系数", width=100, value=0.5, tooltip="车厢受太阳辐射面积系数，一般取值范围为 35%~50%")

    radiation_time, radiation_time_unit, radiation_time_row = create_dropdown_row(label="太阳辐射时长", text_kwargs={"width": 100, "value": 14}, unit_options=["h", "min", "s"], default_unit="h", unit_width=85, tooltip="车厢受太阳辐射时间，通常取值为 12~14 小时")

    # 布局列定义
    opc_col1 = ft.Column([
        ft.Text("工况参数", weight=ft.FontWeight.BOLD, size=18),
        env_temp_row,
        chi_temp_row,
        fro_temp_row,
        chi_relative_humidity,
        fro_relative_humidity,
        env_relative_humidity,
    ])

    opc_col2 = ft.Column([
        ft.Text("辐射参数", weight=ft.FontWeight.BOLD, size=18),
        solar_radiation_row,
        surface_absorptivity_row,
        surface_emissivity_row,
        radiation_area_ratio,
        radiation_time_row,
    ], visible=False)

    operating_parameter_controls = ft.Container(content=ft.Row(controls=[opc_col1, opc_col2], spacing=20, expand=True, vertical_alignment=ft.CrossAxisAlignment.START), expand=True, padding=20)

    # ------------------------------------------------------------
    # 货物参数控件组
    # ------------------------------------------------------------
    open_close_frequency = ft.TextField(label="开关门频次", width=100, value=6, tooltip="24小时内开关门频次，用于计算装卸开门引起的热负荷")
    open_close_frequency_row = ft.Row([open_close_frequency, ft.Text("  1/天", weight=100)])

    # 冷冻货物参数
    fro_specific_heat, fro_specific_heat_row = create_dropdown_values_row(label="比热容", dd_label="常用数值", unit_text="  J/kg·K", preset_options=frozen_goods_prevalues, tooltip="对于冷冻工况，肉类、雪糕等货品为冻品，不存在呼吸热。默认值为猪肉的比热容")

    fro_out_temp, fro_out_temp_unit, fro_out_temp_row = create_two_dropdown_row(label="出库温度", dd_label="常用数值", preset_options=default_fro_out_temp, text_kwargs={'value': -18}, unit_options=["℃", "K"], default_unit="℃", unit_width=80)

    fro_load_mass, _, fro_load_mass_row = create_text_unit_row(label="载重量", unit_text="  吨/天", text_kwargs={"width": 100, "value": 4})

    # 冷藏货物参数
    chi_resp_heat, chi_resp_heat_row = create_dropdown_values_row(label="呼吸热", dd_label="常用数值", unit_text="  mW/kg", preset_options=chilled_goods_prevalues, tooltip="用于蔬果类产生呼吸热的产品，数值参考ASHRAE Handbook Refrigeration。运送温度依据DB35/T 1805-2018短途配送推荐，默认值为土豆的呼吸热")

    chi_load_mass, _, chi_load_mass_row = create_text_unit_row(label="载重量", unit_text="  吨/天", text_kwargs={"width": 100, "value": 4})

    # 预冷参数
    cabin_precool_time, cabin_precool_time_unit, cabin_precool_time_row = create_dropdown_row(label="预冷时长", text_kwargs={"width": 100, "value": 2}, unit_options=["h", "min", "s"], default_unit="h", unit_width=85, tooltip="冷藏车预冷时间（与冷藏货物预冷时间相同），默认值为 2 小时", row_kwargs={"visible": False})

    # 布局列定义
    gpc_col1 = ft.Column([
        ft.Text("运输参数", weight=ft.FontWeight.BOLD, size=18), open_close_frequency_row,
    ], visible=False)

    gpc_col2 = ft.Column([
        ft.Text("冷冻货物参数", weight=ft.FontWeight.BOLD, size=18),
        fro_specific_heat_row,
        fro_load_mass_row,
        fro_out_temp_row,
    ])

    gpc_col3 = ft.Column([
        ft.Text("冷藏货物参数", weight=ft.FontWeight.BOLD, size=18),
        chi_resp_heat_row,
        chi_load_mass_row,
        cabin_precool_time_row,
    ])

    goods_parameter_controls = ft.Container(content=ft.Column(
        [gpc_col1,
        ft.Row([gpc_col2, gpc_col3], spacing=40, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)]),
                                            padding=20)

    # ------------------------------------------------------------
    # 工程参数控件组
    # ------------------------------------------------------------
    safety_coeff = ft.TextField(label="安全系数", width=100, value=1.75, tooltip="根据GB/T 29753要求，制冷机组制冷量应≥1.75倍传热量")

    fan_power, _, fan_power_row = create_text_unit_row(label="风机功率", unit_text="  W", text_kwargs={"width": 100, "value": 90}, tooltip="车厢风机总功率")

    fan_time, fan_time_unit, fan_time_row = create_dropdown_row(label="风机时长", text_kwargs={"width": 100, "value": 14}, unit_options=["h", "min", "s"], default_unit="h")

    light_power, _, light_power_row = create_text_unit_row(label="照明功率", unit_text="  W", text_kwargs={"width": 100, "value": 5})

    light_time, light_time_unit, light_time_row = create_dropdown_row(label="照明时长", text_kwargs={"width": 100, "value": 2}, unit_options=["h", "min", "s"], default_unit="h")

    # ------------------------------------------------------------
    # 高级特性控件组
    # ------------------------------------------------------------

    # 布局列定义
    afc_col1 = ft.Column([ft.Text("电气参数", weight=ft.FontWeight.BOLD, size=18), 
    ft.Row([fan_power_row, light_power_row], spacing=60), 
    ft.Row([fan_time_row, light_time_row], spacing=40)])

    

    afc_col3 = ft.Column([
        ft.Text("工程参数", weight=ft.FontWeight.BOLD, size=18),
        safety_coeff,
    ])

    advanced_feature_controls = ft.Container(content=ft.Column([afc_col1, ft.Row([afc_col3], spacing=100, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)],), padding=20)


    # ------------------------------------------------------------
    # 结果展示控件
    # ------------------------------------------------------------
    # 使用工厂函数统一创建结果字段
    def create_result_cells(label, tooltip, width=80):
        item = ft.Text(value=label, width=80, text_align=ft.TextAlign.LEFT, tooltip=tooltip)
        text = ft.Text(width=width, text_align=ft.TextAlign.LEFT)
        cells = ft.DataRow(
            cells=[
                ft.DataCell(item),
                ft.DataCell(text),
                ft.DataCell(ft.Text("  W", text_align=ft.TextAlign.CENTER)),
            ],)
        return text, cells

    # 电气辐射相关字段
    Q_electric, Q_electric_cells = create_result_cells("电气热负荷", "包括风机和照明负荷的总电气发热功率")
    Q_radiation, Q_radiation_cells = create_result_cells("辐射热负荷", "太阳辐射产生的热负荷")

    electric_Q_Table = ft.DataTable(
        # width=300,
        # column_spacing=20,
        data_row_max_height=40,
        heading_row_height = 40,
        columns=[
            ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
            ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
            ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
        ],
        rows=[Q_electric_cells,],
    )
    radiation_Q_Table = ft.DataTable(
        # width=300,
        # column_spacing=20,
        data_row_max_height=40,
        heading_row_height = 40,
        columns=[
            ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
            ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
            ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
        ],
        rows=[Q_radiation_cells,],
    )

    Q_universal_Table = ft.Row(
            controls=[electric_Q_Table, radiation_Q_Table],
            alignment=ft.MainAxisAlignment.START,  # 确保顶部对齐
            vertical_alignment=ft.CrossAxisAlignment.START,  # 确保子控件在垂直方向上也对齐顶部
            spacing=20
        )


    # 使用工厂函数批量生成其他字段
    Q_wall_chi, Q_wall_chi_cells = create_result_cells("隔热壁传热", "从车厢隔热壁传入的热量")
    Q_leak_chi, Q_leak_chi_cells = create_result_cells("车厢漏热量", "由于车厢密封性不足导致的空气交换带来的热量")
    Q_open_chi, Q_open_chi_cells = create_result_cells("装卸开门热", "因开关门造成的完全空气置换引起的热量增加")
    Q_resp_chi, Q_resp_chi_cells = create_result_cells("呼吸热负荷", "生鲜货物在运输过程中因呼吸作用释放的热量")
    Q_cabin_precool_chi, Q_cabin_precool_chi_cells = create_result_cells("厢体预冷热", "冷藏车预冷过程中消耗的能量")
    Q_goods_precool_chi, Q_goods_precool_chi_cells = create_result_cells("货物预冷热", "冷藏货物预冷过程中的能量消耗")
    Q_total_chi, Q_total_chi_cells = create_result_cells("冷藏总负荷", "所有冷藏热负荷的总和，并乘以安全系数")

    Q_wall_fro, Q_wall_fro_cells = create_result_cells("隔热壁传热", "冷冻工况下通过车厢壁传导的热量")
    Q_leak_fro, Q_leak_fro_cells = create_result_cells("车厢漏热量", "冷冻工况下由于车厢密封性不足导致的空气交换热量")
    Q_open_fro, Q_open_fro_cells = create_result_cells("装卸开门热", "冷冻工况下因开关门导致的完全空气置换热量")
    Q_load_fro, Q_load_fro_cells = create_result_cells("货物热负荷", "冷冻货物与车厢温度差异引起的热负荷")
    Q_cabin_precool_fro, Q_cabin_precool_fro_cells = create_result_cells("厢体预冷热", "冷冻工况下车厢预冷过程中的能量消耗")
    Q_total_fro, Q_total_fro_cells = create_result_cells("冷冻总负荷", "所有冷冻热负荷的总和，并乘以安全系数")

    # 保持可见性设置
    Q_cabin_precool_chi_cells.visible = False
    Q_goods_precool_chi_cells.visible = False
    Q_cabin_precool_fro_cells.visible = False

    fro_Q_Table = ft.Column([
        ft.Text("冷冻负荷: ", weight=ft.FontWeight.BOLD, size=18),
        ft.DataTable(
            # width=300,
            # column_spacing=20,
            data_row_max_height=40,
            heading_row_height = 40,
            columns=[
                ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
                ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
                ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
            ],
            rows=[
                Q_wall_fro_cells,
                Q_leak_fro_cells,
                Q_open_fro_cells,
                Q_load_fro_cells,
                Q_cabin_precool_fro_cells,
                Q_total_fro_cells,
            ],
        )
    ])

    chi_Q_Table = ft.Column([
        ft.Text("冷藏负荷: ", weight=ft.FontWeight.BOLD, size=18),
        ft.DataTable(
            # width=300,
            # column_spacing=20,
            data_row_max_height=40,
            heading_row_height = 40,
            columns=[
                ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
                ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
                ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
            ],
            rows=[
                Q_wall_chi_cells,
                Q_leak_chi_cells,
                Q_open_chi_cells,
                Q_resp_chi_cells,
                Q_cabin_precool_chi_cells,
                Q_goods_precool_chi_cells,
                Q_total_chi_cells,
            ],
        )
    ])

    Q_Table = ft.Row(
            controls=[fro_Q_Table, chi_Q_Table],
            alignment=ft.MainAxisAlignment.START,  # 确保顶部对齐
            vertical_alignment=ft.CrossAxisAlignment.START,  # 确保子控件在垂直方向上也对齐顶部
            spacing=20
        )

    detailed_result_output_control = ft.Container(content=ft.Column([ft.Text("通用负荷: ", weight=ft.FontWeight.BOLD, size=18),Q_universal_Table, ft.Divider(height=10), Q_Table]), padding=20)





    Q_total1_chi, Q_total1_chi_cells = create_result_cells("冷藏总负荷", "所有冷藏热负荷的总和，并乘以安全系数")
    Q_total1_fro, Q_total1_fro_cells = create_result_cells("冷冻总负荷", "所有冷冻热负荷的总和，并乘以安全系数")

    Q_total1_chi_Table = ft.DataTable(
        # width=300,
        # column_spacing=20,
        data_row_max_height=40,
        heading_row_height = 40,
        columns=[
            ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.START),
            ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
            ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
        ],
        rows=[Q_total1_chi_cells,],
    )
    Q_total1_fro_Table = ft.DataTable(
        # width=300,
        # column_spacing=20,
        data_row_max_height=40,
        heading_row_height = 40,
        columns=[
            ft.DataColumn(ft.Text("热负荷"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
            ft.DataColumn(ft.Text("数值", width=80), heading_row_alignment=ft.MainAxisAlignment.CENTER, numeric=True),
            ft.DataColumn(ft.Text("单位"), heading_row_alignment=ft.MainAxisAlignment.CENTER),
        ],
        rows=[Q_total1_fro_cells,],
    )

    Q_total_Table = ft.Row(
            controls=[Q_total1_fro_Table, Q_total1_chi_Table],
            alignment=ft.MainAxisAlignment.START,  # 确保顶部对齐
            vertical_alignment=ft.CrossAxisAlignment.START,  # 确保子控件在垂直方向上也对齐顶部
            spacing=20
        )
    # 新增推荐产品表格
    def create_recommendation_table():
        return ft.DataTable(
            width=200,
            # column_spacing=20,
            data_row_max_height=40,
            heading_row_height=40,
            columns=[
                # 型号 - 左对齐
                ft.DataColumn(ft.Text("型号", text_align=ft.TextAlign.LEFT), numeric=False),

                # 冷藏能力 - 左对齐
                ft.DataColumn(ft.Text("冷藏能力", text_align=ft.TextAlign.LEFT), numeric=False),

                # 冷冻能力 - 左对齐
                ft.DataColumn(ft.Text("冷冻能力", text_align=ft.TextAlign.LEFT), numeric=False),

                # 单位 - 居中对齐
                ft.DataColumn(ft.Text("单位", text_align=ft.TextAlign.CENTER), numeric=False),
            ],
            visible=False
        )
    
    # 首先定义 result_output_tabs
    result_output_tabs = ft.Tabs(
        tabs=[
            ft.Tab(text="仅冷藏", content=ft.Column()),
            ft.Tab(text="仅冷冻", content=ft.Column()),
            ft.Tab(text="全满足", content=ft.Column()),
        ],
    )

    # 创建三个不同的DataTable
    recommendation_table_chilled_only = create_recommendation_table()
    recommendation_table_frozen_only = create_recommendation_table()
    recommendation_table_both = create_recommendation_table()

    # 然后再设置每个 Tab 的内容
    result_output_tabs.tabs[0].content = recommendation_table_chilled_only
    result_output_tabs.tabs[1].content = recommendation_table_frozen_only
    result_output_tabs.tabs[2].content = recommendation_table_both

    # 最后定义 result_output_control
    result_output_control = ft.Container(
        content=ft.Column([
            ft.Text("计算负荷: ", weight=ft.FontWeight.BOLD, size=18),
            Q_total_Table,
            ft.Divider(height=10),
            ft.Text("产品推荐: ", weight=ft.FontWeight.BOLD, size=18),
            ft.Column([result_output_tabs], scroll=ft.ScrollMode.AUTO, height=240)
        ]),
        padding=20
    )

    
    if page.platform == ft.PagePlatform.LINUX or page.platform == ft.PagePlatform.MACOS or page.platform == ft.PagePlatform.WINDOWS:
        if page.platform == ft.PagePlatform.WINDOWS:
            page.window.icon = "logo.ico"  # 窗口图标
        page.window.height = 730
        page.window.width = 790
        page.window.center()
    else:
        page.add(ft.TextButton("Material Button"))
    page.title = __project_name__
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.SYSTEM

    

    # 根据主题模式设置不同图标
    if page.platform_brightness == ft.Brightness.DARK:
        logger.info("当前是黑暗模式")
        RefrTruck_Schematic.src = resource_path("RefrTruck-Schematic-white.png")
    if page.platform_brightness == ft.Brightness.LIGHT:
        logger.info("当前是明亮模式")
        RefrTruck_Schematic.src = resource_path("RefrTruck-Schematic-dark.png")



    # 标题LOGO
    header = ft.Container(content=ft.Row([
        ft.Image(src=resource_path("haier.png"), width=100, fit=ft.ImageFit.CONTAIN),
        ft.Text(__project_name__, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
    ], alignment=ft.MainAxisAlignment.SPACE_EVENLY), padding=10, bgcolor=ft.Colors.GREY_200)
    


    sections = ft.Tabs(
        tabs=[
            ft.Tab(text="车厢参数", content=carriage_parameter_controls),
            ft.Tab(text="工况参数", content=operating_parameter_controls),
            ft.Tab(text="货物参数", content=goods_parameter_controls),
            ft.Tab(text="高级参数", content=advanced_feature_controls,visible=False),
            ft.Tab(text="结果输出", content=result_output_control),
            ft.Tab(text="详细输出", content=detailed_result_output_control,visible=False)
        ],
        expand=True,
    )

    # 高级选项
    calc_advanced = ft.CupertinoSwitch(label="高级",value=False, on_change=lambda e: update_calc_advanced_visible(e, calc_advanced.value))
    
    # 高级换热系数切换
    htc_advanced = ft.Chip(
        label=ft.Text("高级换热"),
        selected=False,
        disabled=True,
        # selected_color=ft.Colors.BLUE_500,
        leading=ft.Icon(ft.Icons.COMPARE_ARROWS),  # 使用 SETTINGS 图标
        shape=ft.StadiumBorder(),
        show_checkmark = False,
        expand=True,
        on_select=lambda e: update_htc_visible(e, htc_advanced.selected, precool.selected),
    )

    # 预冷负荷切换
    precool = ft.Chip(
        label=ft.Text("预冷负荷"),
        selected=False,
        disabled=True,
        # selected_color=ft.Colors.CYAN_500,
        leading=ft.Icon(ft.Icons.AC_UNIT),  # 使用 SNOWING 图标
        shape=ft.StadiumBorder(),
        show_checkmark = False,
        expand=True,
        on_select=lambda e: update_precool_visible(e, htc_advanced.selected, precool.selected),
    )

    # 详细输出切换按钮
    detailed_result_btn = ft.Chip(
        label=ft.Text("详细输出"),
        selected=False,
        # selected_color=ft.Colors.DEEP_PURPLE_300,
        leading=ft.Icon(ft.Icons.LIST_ALT),  # 使用 DETAILS 图标
        shape=ft.StadiumBorder(),
        show_checkmark = False,
        expand=True,
        on_select=lambda e: update_detailed_result_visible(e, detailed_result_btn.selected),
    )
    
    
    # 计算按钮
    calculate_btn = ft.ElevatedButton("求解", icon=ft.Icons.DIRECTIONS_RUN, on_click=lambda e: run(e, sections, htc_advanced.selected, precool.selected), width=120, height=50)


    # 界面布局
    main_column = ft.Column(
        [
            header,
            ft.Container(content=sections, height=485),
            ft.Divider(),
            ft.Row([calc_advanced, htc_advanced, precool, detailed_result_btn, calculate_btn])
        ],
        # expand=True,  # 关键参数2：主列填满整个页面
        spacing=10,
        adaptive=True,
        # scroll=ft.ScrollMode.AUTO  # 添加滚动以防内容溢出
    )



    def open_github(e):
        page.launch_url("https://github.com/YanMing-lxb")

    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=20),
            ft.Container(  # 添加一个Container来包裹ListTile并设置居中对齐
                content=ft.Column(
                    controls=[
                        ft.Image(src=resource_path("jd-xhh.png"), width=120, height=120, fit=ft.ImageFit.CONTAIN),
                        ft.ListTile(title=ft.Text(__team__, weight=ft.FontWeight.BOLD),),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,  # 设置垂直居中对齐
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER  # 设置水平居中对齐
                ),
                alignment=ft.alignment.center  # 设置居中对齐
            ),
            ft.Divider(height=1, color=ft.Colors.GREY_300),  # 添加分隔线
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON),  # 使用 PERSON 图标
                title=ft.Text(__author__)),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.HOME),  # 使用占位符图标
                title=ft.Text("项目主页"),
                on_click=open_github),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.LABEL),  # 使用占位符图标
                title=ft.Text(f"版本: {__version__}")),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DATE_RANGE),  # 使用占位符图标
                title=ft.Text(f"更新时间: {__date__}")),
        ],)

    # 新增：创建主题切换按钮
    theme_icon = ft.Icon(name=ft.Icons.LIGHT_MODE)  # 默认显示日间模式图标
    
    def toggle_theme(e):
        # 切换页面主题模式
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        
        # 更新图标
        theme_icon.name = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.LIGHT_MODE
        
        # 更新冷藏车示意图的显示
        if page.theme_mode == ft.ThemeMode.DARK:
            RefrTruck_Schematic.src = resource_path("RefrTruck-Schematic-white.png")
        else:
            RefrTruck_Schematic.src = resource_path("RefrTruck-Schematic-dark.png")
        
        page.update()

    page.appbar = ft.AppBar(
        adaptive=True,
        toolbar_height=30,
        actions=[
            ft.IconButton(
                icon=theme_icon.name,
                on_click=toggle_theme,
                tooltip="切换日间/夜间模式"
            )
        ]
    )

    page.add(main_column)



    def run(e, sections, htc_advanced, precool):
        page = e.page

        logger.info("-----------开始计算-----------")
        
        inputs = get_inputs()
        logger.info(f"获得输入: {inputs}")
        # 执行校验
        logger.info("-----------校验输入-----------")
        if errors := validate_inputs(inputs, htc_advanced, precool):
            logger.error(f"输入校验未通过：{"  ".join(errors)}")
            message_show(page, f"输入校验未通过：{"  ".join(errors)}", 'error')
        else:
            hlc = HLC(inputs, page, message_show)
            try:
                logger.info("-----------获取结果-----------")
                result = hlc.calculate_all(htc_advanced, precool)
                formatted_result = {}
                logger.info("----------格式化结果----------")
                for key, value in result.items():
                    try:
                        # 尝试将值转换为float
                        float_value = float(value)
                        # 保留两位小数
                        formatted_result[key] = round(float_value, 2)
                    except ValueError:
                        # 如果转换失败，保留原值
                        formatted_result[key] = value
                logger.info(f"计算结果为: {formatted_result}")  # 调试输出，确认键名

                logger.info("-----------上传结果-----------")
                for k, v in formatted_result.items():
                    Q_output[k].value=v
                
                # 新增：执行推荐逻辑并更新表格
                update_recommendations(formatted_result["Q_total1_chi"], formatted_result["Q_total1_fro"], result_output_tabs, env_temp, chi_temp, fro_temp, product_info, page)
                

                visible_tabs = [i for i, tab in enumerate(sections.tabs) if tab.visible]
                if visible_tabs:
                    sections.selected_index = len(visible_tabs)-1 # “输出参数”是最后一个Tab
                logger.info("-----------结束计算-----------")
            except Exception as ex:  # 捕获具体异常对象
                logger.info("-----------发生错误-----------")
                logger.error(f"计算过程中发生错误: {str(ex)}", exc_info=True)  # 添加完整堆栈信息
                message_show(page, f"发生错误: {str(ex)}", 'error')  # 显示具体错误
            
            page.update()

    Q_output = {
        "Q_electric": Q_electric,
        "Q_radiation": Q_radiation,
        "Q_wall_chi": Q_wall_chi,
        "Q_leak_chi":Q_leak_chi,
        "Q_open_chi": Q_open_chi,
        "Q_resp_chi": Q_resp_chi,
        "Q_cabin_precool_chi": Q_cabin_precool_chi,
        "Q_goods_precool_chi": Q_goods_precool_chi,
        "Q_total_chi": Q_total_chi,
        "Q_total_fro": Q_total_fro,
        "Q_total1_chi": Q_total1_chi,
        "Q_total1_fro": Q_total1_fro,
        "Q_wall_fro": Q_wall_fro,
        "Q_leak_fro": Q_leak_fro,
        "Q_open_fro": Q_open_fro,
        "Q_load_fro": Q_load_fro,
        "Q_cabin_precool_fro": Q_cabin_precool_fro,
    }

    def get_inputs():
        carriage_parameter_controls_dict = {
            'length': length.value,
            'length_unit': length_unit.value,
            'width': width.value,
            'width_unit': width_unit.value,
            'height': height.value,
            'height_unit': height_unit.value,
            'thickness': thickness.value,
            'thickness_unit': thickness_unit.value,
            'speed': speed.value,
            'speed_unit': speed_unit.value,
            'leak_multiple': leak_multiple.value,
            'density_walls': density_walls.value,
            'specific_heat_walls': specific_heat_walls.value,
            'thermal_cond_walls': thermal_cond_walls.value,
            'thickness_walls': thickness_walls.value,
            'thickness_walls_unit': thickness_walls_unit.value
        }

        operating_parameter_controls_dict = {
            'env_temp': env_temp.value,
            'env_temp_unit': env_temp_unit.value,
            'chi_temp': chi_temp.value,
            'chi_temp_unit': chi_temp_unit.value,
            'fro_temp': fro_temp.value,
            'fro_temp_unit': fro_temp_unit.value,
            'chi_relative_humidity': chi_relative_humidity.value,
            'fro_relative_humidity': fro_relative_humidity.value,
            'env_relative_humidity': env_relative_humidity.value,
            'solar_radiation': solar_radiation.value,
            'surface_absorptivity': surface_absorptivity.value,
            'surface_emissivity': surface_emissivity.value,
            'radiation_area_ratio': radiation_area_ratio.value,
            'radiation_time': radiation_time.value,
            'radiation_time_unit': radiation_time_unit.value
        }

        goods_parameter_controls_dict = {
            'open_close_frequency': open_close_frequency.value,
            'fro_specific_heat': fro_specific_heat.value,
            'fro_out_temp': fro_out_temp.value,
            'fro_out_temp_unit': fro_out_temp_unit.value,
            'fro_load_mass': fro_load_mass.value,
            'chi_resp_heat': chi_resp_heat.value,
            'chi_load_mass': chi_load_mass.value,
            'cabin_precool_time': cabin_precool_time.value,
            'cabin_precool_time_unit': cabin_precool_time_unit.value
        }

        advanced_feature_controls_dict = {
            # 工程参数
            'safety_coeff': safety_coeff.value,
            
            # 电气参数
            'fan_power': fan_power.value,
            'fan_time': fan_time.value,
            'fan_time_unit': fan_time_unit.value,
            'light_power': light_power.value,
            'light_time': light_time.value,
            'light_time_unit': light_time_unit.value,
            
            # 换热参数
            'thermal_bridging_coeff': thermal_bridging_coeff.value,
            'htc': htc.value,
            'beta': beta.value,               # 虽然当前不可见，保留字段
            'diff_insuf_with_inair': diff_insuf_with_inair.value  # 虽然当前不可见，保留字段
        }


        inputs_dict = carriage_parameter_controls_dict | operating_parameter_controls_dict | goods_parameter_controls_dict|advanced_feature_controls_dict

        # 将能转换为float的值转换为float
        for key in inputs_dict:
            if 'unit' not in key:
                try:
                    inputs_dict[key] = float(inputs_dict[key])
                except ValueError:
                    pass  # 如果转换失败，保持原值
        return inputs_dict

    def validate_inputs(inputs_dict, htc_advanced, precool):
        """输入校验逻辑"""
        errors = []
        # 构建豁免字段集合
        skip_required = set()
        # 根据开关状态设置豁免字段
        if not htc_advanced:
            skip_required.update({'speed', 'thermal_cond_walls', 'thickness_walls', 
                                'thermal_bridging_coeff', 'beta', 
                                'diff_insuf_with_inair', 'htc'})
            
        if not precool:
            skip_required.update({'density_walls', 'specific_heat_walls', 
                                'thickness_walls'})
        # 必填校验
        for key, value in inputs_dict.items():
            if key in skip_required:
                continue
                
            if value in (None, '') and 'unit' not in key:
                var = globals()[key]
                errors.append(f"{var.label}: 不能为空")
                
                    
        # 数值有效性校验
        if not errors:
            for key, value in inputs_dict.items():
                if any(k in key for k in ['unit', '_unit']):
                    continue
                    
                if key in skip_required:
                    continue
                
                if key in ('density_walls', 'specific_heat_walls', 'thermal_cond_walls', 'thickness_walls'):
                    continue
                    
                try:
                    float(value)
                except ValueError:
                    var = globals()[key]
                    errors.append(f"{var.label}: 必须为有效数字")

        # 特殊范围校验（仅当数值有效时执行）
        if not errors:
            special_checks = {
                'length': (0 <= float(inputs_dict['length']), "长应大于0"),
                'width': (0 <= float(inputs_dict['width']), "宽应大于0"),
                'height': (0 <= float(inputs_dict['height']), "高应大于0"),
                'thickness': (0 <= float(inputs_dict['thickness']), "厚度应大于0"),
                'speed': (0 <= float(inputs_dict['speed']), "车速应大于0"),
                'leak_multiple': (0 < float(inputs_dict['leak_multiple']) <= 10, "漏气倍数应在0-10之间"),
                'safety_coeff': (float(inputs_dict['safety_coeff']) >= 1, "冗余系数应≥1"),
                'surface_absorptivity': (0 <= float(inputs_dict['surface_absorptivity']) <= 1, "吸收率应为0-1之间的小数"),
                'surface_emissivity': (0 <= float(inputs_dict['surface_emissivity']) <= 1, "发射率应为0-1之间的小数"),
                'radiation_area_ratio': (0 <= float(inputs_dict['radiation_area_ratio']) <= 1, "辐射面积系数应为0-1之间的小数"),
                'radiation_time': (0 <= float(inputs_dict['radiation_time']) <= 24, "一天内的辐射时长应为0-24之间的数"),
                'chi_relative_humidity': (0 <= float(inputs_dict['chi_relative_humidity']) <= 1, "冷藏相对湿度应为0-1之间的小数"),
                'fro_relative_humidity': (0 <= float(inputs_dict['fro_relative_humidity']) <= 1, "冷冻相对湿度应为0-1之间的小数"),
                'env_relative_humidity': (0 <= float(inputs_dict['env_relative_humidity']) <= 1, "环境相对湿度应为0-1之间的小数"),

            }
            
            for name, (condition, msg) in special_checks.items():
                try:
                    if not condition:
                        errors.append(msg)
                except:
                    continue  # 已在前面的校验中捕获错误

        return errors

    def update_calc_advanced_visible(e,calc_adv_visible):
        width_row.visible = calc_adv_visible
        height_row.visible = calc_adv_visible
        thickness_row.visible = calc_adv_visible
        leak_multiple_row.visible = calc_adv_visible

        htc_advanced.disabled = not calc_adv_visible
        precool.disabled = not calc_adv_visible
        if not calc_adv_visible:
            htc_advanced.value = False
            cabin_parameters_show.visible = False
            thickness_walls_row.visible = False
            density_walls_row.visible = False
            specific_heat_walls_row.visible = False
            thermal_cond_walls_row.visible = False
            thermal_bridging_coeff_row.visible = False
            beta_row.visible = False
            diff_insuf_with_inair_row.visible = False

            
            precool.value = False
            cabin_precool_time_row.visible = False
            Q_goods_precool_chi_cells.visible = False
            Q_cabin_precool_chi_cells.visible = False
            Q_cabin_precool_fro_cells.visible = False
            
            RefrTruck_Schematic_Text.visible = True
            RefrTruck_Schematic.visible = True
            RefrTruck_Schematic.width = 350
            carriage_parameter.spacing = 20

        chi_relative_humidity.visible = calc_adv_visible
        fro_relative_humidity.visible = calc_adv_visible
        env_relative_humidity.visible = calc_adv_visible

        opc_col2.visible = calc_adv_visible

        gpc_col1.visible = calc_adv_visible

        sections.tabs[3].visible = calc_adv_visible

        e.page.update()

    def update_htc_visible(e, htc_visible, precool_visible):
        speed_row.visible = htc_visible
        if htc_visible or precool_visible:
            cabin_parameters_show.visible = True
            thickness_walls_row.visible = True
        else:
            cabin_parameters_show.visible = False
            thickness_walls_row.visible = False
        
        if precool_visible and htc_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.visible = False
        if precool_visible and not htc_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.visible = True
            RefrTruck_Schematic.width = 240
            carriage_parameter.spacing = 80
        if not precool_visible and htc_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.width = 280
            carriage_parameter.spacing = 80
        if not precool_visible and not htc_visible:
            RefrTruck_Schematic_Text.visible = True
            RefrTruck_Schematic.visible = True
            RefrTruck_Schematic.width = 350
            carriage_parameter.spacing = 20

        thermal_cond_walls_row.visible = htc_visible
        

        thermal_bridging_coeff_row.visible = htc_visible
        beta_row.visible = htc_visible
        diff_insuf_with_inair_row.visible = htc_visible

        htc_row.visible = not htc_visible
        e.page.update()

    def update_precool_visible(e, htc_visible, precool_visible):
        if htc_visible or precool_visible:
            cabin_parameters_show.visible = True
            thickness_walls_row.visible = True
        else:
            cabin_parameters_show.visible = False
            thickness_walls_row.visible = False

        if htc_visible and precool_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.visible = False
        if htc_visible and not precool_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.visible = True
            RefrTruck_Schematic.width = 280
            carriage_parameter.spacing = 80
        if not htc_visible and precool_visible:
            RefrTruck_Schematic_Text.visible = False
            RefrTruck_Schematic.width = 240
            carriage_parameter.spacing = 80
        if not htc_visible and not precool_visible:
            RefrTruck_Schematic_Text.visible = True
            RefrTruck_Schematic.visible = True
            RefrTruck_Schematic.width = 350
            carriage_parameter.spacing = 20

        density_walls_row.visible = precool_visible
        specific_heat_walls_row.visible = precool_visible
        cabin_precool_time_row.visible = precool_visible

        Q_goods_precool_chi_cells.visible = precool_visible
        Q_cabin_precool_chi_cells.visible = precool_visible
        Q_cabin_precool_fro_cells.visible = precool_visible
        e.page.update()

    def update_detailed_result_visible(e, detailed_visible):
        sections.tabs[5].visible = detailed_visible
        visible_tabs = [i for i, tab in enumerate(sections.tabs) if tab.visible]
        sections.selected_index = len(visible_tabs)-1
        e.page.update()
        

ft.app(target=main)

