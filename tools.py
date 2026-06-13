from motor import Motor

# 按轴名自动创建 Motor 实例
motors: dict[str, Motor] = {}
connected = False


def get_motor(axis: str) -> Motor:
    if axis not in motors:
        motors[axis] = Motor(axis)
        if connected:
            motors[axis].is_connected = True
    return motors[axis]


def motor_connect(cont_stus: int) -> str:
    global connected
    connected = cont_stus == 1
    for m in motors.values():
        m.is_connected = connected
    if connected:
        print("连接成功")
        return "连接成功"
    else:
        print("未连接")
        return "未连接"


def motor_status() -> str:
    status = "已连接" if connected else "未连接"
    print(f"电机状态：{status}")
    return status


def move_rel(axis: str, dist: float) -> str:
    motor = get_motor(axis)
    result = motor.move_rel(dist)
    print(result)
    return result


TOOL_REGISTRY = {
    "motor_connect": motor_connect,
    "motor_status": motor_status,
    "move_rel": move_rel,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "motor_connect",
        "description": "与电机建立连接，使用电机前需先调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "cont_stus": {
                    "type": "integer",
                    "description": "连接状态，1 表示连接，0 表示断开。"
                }
            },
            "required": ["cont_stus"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "motor_status",
        "description": '查询电机当前连接状态，返回"已连接"或"未连接"。',
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "move_rel",
        "description": "使电机进行相对步进运动, 用户指示电机相对运动时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "axis": {
                    "type": "string",
                    "description": "运动轴名称，例如：X, Y, Z, R, 1, 2, 3等。"
                },
                "dist": {
                    "type": "number",
                    "description": "相对运动的距离，正数正向，负数负向。"
                }
            },
            "required": ["axis", "dist"]
        }
    }
}]
