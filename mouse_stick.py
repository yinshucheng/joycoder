#!/usr/bin/env python3
"""阶段 1 happy-path：推右摇杆 → 鼠标光标移动。

已验证：pyjoycon 稳定读右摇杆。
摇杆范围（实测）：h 741~3461 中心~2101；v 783~2986 中心~1884。
归一化后映射为鼠标速度，推得越远移动越快。
"""
import time
from pyjoycon import JoyCon
from pyjoycon.constants import JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID
from pynput.mouse import Controller

# 摇杆标定（实测值）
H_CENTER, H_MIN, H_MAX = 2101, 741, 3461
V_CENTER, V_MIN, V_MAX = 1884, 783, 2986
DEADZONE = 0.15      # 死区，防漂移
MAX_SPEED = 18.0     # 满推时每帧移动像素
POLL_HZ = 120        # 轮询频率

mouse = Controller()
jc = JoyCon(JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID)
print("摇杆控鼠标已启动。推右摇杆移动光标，Ctrl+C 退出。")


def norm(raw, center, lo, hi):
    """归一化到 [-1,1]，加死区。"""
    if raw <= 0:
        return 0.0
    if raw >= center:
        v = (raw - center) / max(1, hi - center)
    else:
        v = (raw - center) / max(1, center - lo)
    v = max(-1.0, min(1.0, v))
    if abs(v) < DEADZONE:
        return 0.0
    # 死区外重新映射到 0~1，并平方加速（精细控制 + 快速移动兼顾）
    sign = 1 if v > 0 else -1
    mag = (abs(v) - DEADZONE) / (1 - DEADZONE)
    return sign * mag * mag


period = 1.0 / POLL_HZ
while True:
    s = jc.get_status()["analog-sticks"]["right"]
    h, v = s["horizontal"], s["vertical"]
    nx = norm(h, H_CENTER, H_MIN, H_MAX)
    ny = norm(v, V_CENTER, V_MIN, V_MAX)
    if nx or ny:
        dx = nx * MAX_SPEED
        dy = -ny * MAX_SPEED  # 摇杆上(v大)→屏幕上(y减小)，取反
        x, y = mouse.position
        mouse.position = (x + dx, y + dy)
    time.sleep(period)
