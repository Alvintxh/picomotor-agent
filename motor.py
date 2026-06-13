class Motor:
    def __init__(self, axis: str, limits: tuple = (-10000, 10000), speed: float = 1000):
        self.axis = axis
        self.home_pos = 0
        self.current_pos = 0
        self.is_connected = False
        self.speed = speed
        self.limits = limits

    def connect(self):
        self.is_connected = True
        return "连接成功"

    def disconnect(self):
        self.is_connected = False
        return "已断开"

    def move_rel(self, dist: float) -> str:
        if not self.is_connected:
            return "错误：电机未连接"
        new_pos = self.current_pos + dist
        if not (self.limits[0] <= new_pos <= self.limits[1]):
            return f"错误：超出行程限位 {self.limits}"
        self.current_pos = new_pos
        return f"轴{self.axis}成功相对运动{dist}步，当前位置：{self.current_pos}"
