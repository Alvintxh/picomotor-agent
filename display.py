from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_motor_status(motors: dict, connected: bool) -> None:
    if not motors:
        return

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("轴", style="bold")
    table.add_column("连接", justify="center")
    table.add_column("当前位置", justify="right")
    table.add_column("归零位置", justify="right")
    table.add_column("速度 (steps/s)", justify="right")
    table.add_column("限位", justify="center")

    for axis, motor in motors.items():
        conn_text = Text("● 已连接", style="green") if motor.is_connected else Text("○ 未连接", style="red")
        table.add_row(
            axis,
            conn_text,
            str(motor.current_pos),
            str(motor.home_pos),
            str(motor.speed),
            f"{motor.limits[0]} ~ {motor.limits[1]}",
        )

    console.print(Panel(table, title="[bold]电机状态[/bold]", border_style="blue"))
