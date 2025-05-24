import logging
import flet as ft
from bisect import bisect_left
logger = logging.getLogger(__name__)


def interpolate_2d(matrix: list, env_temps: list, target_temps: list, env_temp_val: float, chi_temp_val: float,
                    fro_temp_val: float) -> tuple:
    """二维线性插值函数，用于获取指定环境温度和目标温度下的冷藏与冷冻能力

    Parameters
    ----------
    matrix : list
        二维数组，行对应不同环境温度，列对应不同目标温度
    env_temps : list
        环境温度列表（升序）
    target_temps : list
        目标温度列表（升序）
    env_temp_val : float
        当前环境温度值
    chi_temp_val : float
        冷藏目标温度值
    fro_temp_val : float
        冷冻目标温度值

    Returns
    -------
    tuple
        (chilled_capacity, frozen_capacity) 插值结果或 None
    """
    def find_index(temp_list, value):
        idx = bisect_left(temp_list, value)
        if idx == 0:
            return 0, 0
        elif idx == len(temp_list):
            return len(temp_list) - 1, len(temp_list) - 1
        else:
            return idx - 1, idx

    def interpolate(x, x0, x1, y0, y1):
        if x0 == x1:
            return y0
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    try:
        env_idx_low, env_idx_high = find_index(env_temps, env_temp_val)
        env_low = env_temps[env_idx_low]
        env_high = env_temps[env_idx_high]

        chi_idx_low, chi_idx_high = find_index(target_temps, chi_temp_val)
        temp_low = target_temps[chi_idx_low]
        temp_high = target_temps[chi_idx_high]

        fro_idx_low, fro_idx_high = find_index(target_temps, fro_temp_val)
        fro_temp_low = target_temps[fro_idx_low]
        fro_temp_high = target_temps[fro_idx_high]

        def get_value(i, j):
            if i < len(matrix) and j < len(matrix[i]):
                val = matrix[i][j]
                return float(val) if val not in ("", None) else None
            return None

        q11 = get_value(env_idx_low, chi_idx_low)
        q12 = get_value(env_idx_low, chi_idx_high)
        q21 = get_value(env_idx_high, chi_idx_low)
        q22 = get_value(env_idx_high, chi_idx_high)

        if None not in (q11, q12, q21, q22):
            top = interpolate(chi_temp_val, temp_low, temp_high, q11, q12)
            bottom = interpolate(chi_temp_val, temp_low, temp_high, q21, q22)
            chilled_capacity = interpolate(env_temp_val, env_low, env_high, top, bottom)
        else:
            candidates = [x for x in [q11, q12, q21, q22] if x is not None]
            chilled_capacity = candidates[0] if candidates else None

        q11_f = get_value(env_idx_low, fro_idx_low)
        q12_f = get_value(env_idx_low, fro_idx_high)
        q21_f = get_value(env_idx_high, fro_idx_low)
        q22_f = get_value(env_idx_high, fro_idx_high)

        if None not in (q11_f, q12_f, q21_f, q22_f):
            top_f = interpolate(fro_temp_val, fro_temp_low, fro_temp_high, q11_f, q12_f)
            bottom_f = interpolate(fro_temp_val, fro_temp_low, fro_temp_high, q21_f, q22_f)
            frozen_capacity = interpolate(env_temp_val, env_low, env_high, top_f, bottom_f)
        else:
            candidates_f = [x for x in [q11_f, q12_f, q21_f, q22_f] if x is not None]
            frozen_capacity = candidates_f[0] if candidates_f else None

        return chilled_capacity, frozen_capacity

    except Exception as e:
        logger.error(f"插值过程中发生错误：{str(e)}", exc_info=True)
        return None, None


def update_recommendations(chi_load, fro_load, result_output_tabs, env_temp, chi_temp, fro_temp, product_info, page):
    chi_load = float(chi_load or 0)
    fro_load = float(fro_load or 0)

    table_chilled_only = result_output_tabs.tabs[0].content
    table_frozen_only = result_output_tabs.tabs[1].content
    table_both = result_output_tabs.tabs[2].content

    for table in [table_chilled_only, table_frozen_only, table_both]:
        table.rows.clear()

    if chi_load <= 0 and fro_load <= 0:
        for table in [table_chilled_only, table_frozen_only, table_both]:
            table.visible = False
        page.update()
        return

    products_chilled_only = []
    products_frozen_only = []
    products_both = []

    env_temp_val = float(env_temp.value)
    chi_temp_val = float(chi_temp.value)
    fro_temp_val = float(fro_temp.value)

    for product, specs in product_info.items():
        logger.debug(f"正在处理产品：{product}, 配置为：{specs}")

        if "env_temps" not in specs or "target_temps" not in specs or "cooling_capacity" not in specs:
            logger.warning(f"产品 {product} 缺少必要字段，跳过插值")
            continue

        env_temps = specs["env_temps"]
        target_temps = specs["target_temps"]
        matrix = specs["cooling_capacity"]

        chilled_capacity, frozen_capacity = interpolate_2d(
            matrix, env_temps, target_temps, env_temp_val, chi_temp_val, fro_temp_val
        )

        if chilled_capacity is None or frozen_capacity is None:
            continue

        chilled_capacity = float(chilled_capacity)
        frozen_capacity = float(frozen_capacity)

        can_chilled = chilled_capacity >= float(chi_load)
        can_frozen = frozen_capacity >= float(fro_load)

        if can_chilled:
            products_chilled_only.append((product, chilled_capacity, frozen_capacity))

        if can_frozen:
            products_frozen_only.append((product, chilled_capacity, frozen_capacity))

        if can_chilled and can_frozen:
            products_both.append((product, chilled_capacity, frozen_capacity))

    def add_rows(table, products):
        for model, chilled, frozen in products:
            cells = [
                ft.DataCell(ft.Text(model, text_align=ft.TextAlign.LEFT)),
                ft.DataCell(ft.Text(str(chilled), text_align=ft.TextAlign.LEFT)),
                ft.DataCell(ft.Text(str(frozen), text_align=ft.TextAlign.LEFT)),
                ft.DataCell(ft.Text("  W", text_align=ft.TextAlign.CENTER)),
            ]
            table.rows.append(ft.DataRow(cells=cells))
        table.visible = True

    add_rows(table_chilled_only, products_chilled_only)
    add_rows(table_frozen_only, products_frozen_only)
    add_rows(table_both, products_both)

    def set_empty_message(table, message):
        if len(table.rows) == 0:
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(message, color=ft.Colors.RED_500)),
                    ft.DataCell(ft.Text("N/A")),
                    ft.DataCell(ft.Text("N/A")),
                    ft.DataCell(ft.Text("  W")),
                ])
            )

    set_empty_message(table_chilled_only, "无仅冷藏产品")
    set_empty_message(table_frozen_only, "无仅冷冻产品")
    set_empty_message(table_both, "无同时满足产品")

    table_chilled_only.visible = len(table_chilled_only.rows) > 0
    table_frozen_only.visible = len(table_frozen_only.rows) > 0
    table_both.visible = len(table_both.rows) > 0

    page.update()