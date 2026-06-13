import dearpygui.dearpygui as dpg

import tools

HISTORY_LEN = 200
position_histories: dict[str, list[float]] = {}
registered_axes: set[str] = set()


def add_axis_panel(axis: str):
    motor = tools.motors[axis]
    with dpg.collapsing_header(label=f"轴 {axis}", default_open=True, parent="main_window"):
        with dpg.group(horizontal=True):
            with dpg.group(width=180):
                dpg.add_text("连接状态")
                dpg.add_text("未连接", tag=f"conn_{axis}", color=(220, 80, 80))
                dpg.add_spacer(height=8)
                dpg.add_text("当前位置")
                dpg.add_text("0", tag=f"pos_{axis}", color=(255, 255, 100))
                dpg.add_spacer(height=8)
                dpg.add_text("速度 (steps/s)")
                dpg.add_text(str(motor.speed), tag=f"speed_{axis}")
                dpg.add_spacer(height=8)
                dpg.add_text("行程限位")
                dpg.add_text(f"{motor.limits[0]} ~ {motor.limits[1]}", tag=f"limits_{axis}")

            with dpg.plot(label=f"位置历史", height=180, width=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label="帧", tag=f"xaxis_{axis}", no_gridlines=True)
                dpg.set_axis_limits(f"xaxis_{axis}", 0, HISTORY_LEN)
                with dpg.plot_axis(dpg.mvYAxis, label="步", tag=f"yaxis_{axis}"):
                    dpg.add_line_series([], [], label="位置", tag=f"series_{axis}")

        dpg.add_spacer(height=4)


def update_frame():
    if tools.connected:
        dpg.set_value("global_conn", "● 已连接")
        dpg.configure_item("global_conn", color=(80, 220, 80))
    else:
        dpg.set_value("global_conn", "○ 未连接")
        dpg.configure_item("global_conn", color=(220, 80, 80))

    for axis, motor in list(tools.motors.items()):
        if axis not in registered_axes:
            if dpg.does_item_exist("placeholder"):
                dpg.delete_item("placeholder")
            add_axis_panel(axis)
            position_histories[axis] = [0.0] * HISTORY_LEN
            registered_axes.add(axis)

        hist = position_histories[axis]
        hist.append(float(motor.current_pos))
        hist.pop(0)

        dpg.set_value(f"series_{axis}", [list(range(HISTORY_LEN)), hist])
        dpg.set_axis_limits(f"yaxis_{axis}",
                            min(hist) - 10,
                            max(hist) + 10)

        dpg.set_value(f"pos_{axis}", str(motor.current_pos))

        if motor.is_connected:
            dpg.set_value(f"conn_{axis}", "● 已连接")
            dpg.configure_item(f"conn_{axis}", color=(80, 220, 80))
        else:
            dpg.set_value(f"conn_{axis}", "○ 未连接")
            dpg.configure_item(f"conn_{axis}", color=(220, 80, 80))


def run_gui():
    dpg.create_context()
    dpg.create_viewport(title="Picomotor Agent", width=720, height=560, min_width=400, min_height=300)

    with dpg.window(tag="main_window", no_title_bar=True, no_move=True, no_resize=True):
        dpg.add_text("Picomotor 控制面板", color=(255, 200, 60))
        dpg.add_separator()
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_text("全局连接状态：")
            dpg.add_text("○ 未连接", tag="global_conn", color=(220, 80, 80))
        dpg.add_separator()
        dpg.add_spacer(height=4)
        dpg.add_text("等待轴运动...", tag="placeholder", color=(150, 150, 150))

    with dpg.font_registry():
        with dpg.font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16) as default_font:
            pass
    dpg.bind_font(default_font)

    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (30, 30, 35))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 45, 52))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (60, 90, 130))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (70, 110, 160))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)

    dpg.bind_theme(global_theme)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

    while dpg.is_dearpygui_running():
        update_frame()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
