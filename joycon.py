#!/usr/bin/env python3
"""Joy-Con 控鼠标 + 按键 DIY 映射（语音编程辅助）。

右摇杆 → 鼠标移动；面板按键 → 可配置动作（点击/回车/删除/快捷键）。

运行：
  DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/hidapi/0.15.0/lib .venv312/bin/python joycon.py

需 macOS 辅助功能权限（系统设置→隐私与安全性→辅助功能，给终端授权）。
"""
import time
from pyjoycon import JoyCon
from pyjoycon.constants import JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID
from pynput.mouse import Controller as MouseCtl, Button
from pynput.keyboard import Controller as KeyCtl, Key
import Quartz

# Fn 键模拟（长按型，用于豆包语音输入）。实测可唤起豆包听写。
_FN_KEYCODE = 0x3F

def fn_down():
    ev = Quartz.CGEventCreateKeyboardEvent(None, _FN_KEYCODE, True)
    Quartz.CGEventSetType(ev, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskSecondaryFn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def fn_up():
    ev = Quartz.CGEventCreateKeyboardEvent(None, _FN_KEYCODE, False)
    Quartz.CGEventSetType(ev, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

# ============== 配置区（DIY 改这里）==============

# 摇杆控鼠标参数
H_CENTER, H_MIN, H_MAX = 2101, 741, 3461
V_CENTER, V_MIN, V_MAX = 1884, 783, 2986
DEADZONE = 0.15      # 死区（防漂移）
MAX_SPEED = 20.0     # 满推时每帧移动像素
POLL_HZ = 120
DEBOUNCE = 0.30      # 点击型按键防抖窗口（秒）：按一下只触发一次，防抖动连发

# 按键映射：按键名 → 动作
# 边沿触发型（按下瞬间执行一次）：
#   ("click", Button.left)          鼠标左键点击
#   ("click", Button.right)         鼠标右键点击
#   ("key", Key.enter)              按一个键
#   ("key", Key.backspace)          删除
#   ("combo", [Key.cmd, 'c'])       组合键 Cmd+C
#   ("shell", "command")            执行 shell 命令
# 长按型（按住=按下，松开=松开）：
#   ("hold_fn",)                    长按 Fn（豆包语音：按住说话，松开结束）
# 按键名（右 Joy-Con）：right.a right.b right.x right.y right.r right.zr
#                       shared.plus shared.home
MAPPING = {
    "right.zr":   ("hold_fn",),              # ZR 扳机 = 长按说话（语音输入）★
    "right.a":    ("click", Button.left),    # A = 左键点击
    "right.b":    ("key", Key.enter),        # B = 回车
    "right.x":    ("key", Key.backspace),    # X = 删除
    "right.y":    ("click", Button.right),   # Y = 右键点击
}

# ===============================================

mouse = MouseCtl()
kb = KeyCtl()


def norm(raw, center, lo, hi):
    if raw <= 0:
        return 0.0
    if raw >= center:
        v = (raw - center) / max(1, hi - center)
    else:
        v = (raw - center) / max(1, center - lo)
    v = max(-1.0, min(1.0, v))
    if abs(v) < DEADZONE:
        return 0.0
    sign = 1 if v > 0 else -1
    mag = (abs(v) - DEADZONE) / (1 - DEADZONE)
    return sign * mag * mag


HOLD_KINDS = {"hold_fn"}  # 长按型动作（按下/松开都要处理）


def do_press(action):
    """按键按下时执行。"""
    kind = action[0]
    if kind == "click":
        mouse.click(action[1])
    elif kind == "key":
        kb.press(action[1]); kb.release(action[1])
    elif kind == "combo":
        keys = action[1]
        for k in keys:
            kb.press(k)
        for k in reversed(keys):
            kb.release(k)
    elif kind == "shell":
        import subprocess
        subprocess.Popen(action[1], shell=True)
    elif kind == "hold_fn":
        fn_down()


def do_release(action):
    """长按型按键松开时执行。"""
    if action[0] == "hold_fn":
        fn_up()


def flatten(status_buttons):
    """把 buttons dict 拍平成 set of 'group.key'。"""
    on = set()
    for grp in ("right", "shared", "left"):
        for k, v in status_buttons.get(grp, {}).items():
            if v:
                on.add(f"{grp}.{k}")
    return on


def connect():
    """等手柄出现并连上。手柄没开/没连时持续等待，不崩溃。"""
    from pyjoycon.device import get_device_ids
    waited = False
    while True:
        ids = [i for i in get_device_ids() if i[1] == JOYCON_R_PRODUCT_ID]
        if ids:
            try:
                jc = JoyCon(JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID)
                print("✓ 手柄已连接")
                return jc
            except Exception as e:
                print(f"连接失败，重试: {e}")
        elif not waited:
            print("等待手柄连接...（蓝牙连上右 Joy-Con）", flush=True)
            waited = True
        time.sleep(2)


def main():
    print("Joy-Con 控制已启动。")
    print("  右摇杆 → 移动鼠标")
    for key, act in MAPPING.items():
        print(f"  {key} → {act}")
    print("Ctrl+C 退出。\n")

    jc = connect()
    prev_buttons = set()
    last_press = {}     # key -> 上次触发按下的时间戳（防抖）
    fn_held = False     # Fn 是否被按住（断线安全）
    period = 1.0 / POLL_HZ
    while True:
        # 读状态，断线则安全松开 Fn + 自动重连
        try:
            status = jc.get_status()
        except Exception as e:
            print(f"⚠️ 手柄断线: {e}")
            if fn_held:
                fn_up(); fn_held = False
                print("  （已安全松开 Fn）")
            prev_buttons = set()
            jc = connect()
            continue

        # 摇杆控鼠标
        s = status["analog-sticks"]["right"]
        nx = norm(s["horizontal"], H_CENTER, H_MIN, H_MAX)
        ny = norm(s["vertical"], V_CENTER, V_MIN, V_MAX)
        if nx or ny:
            x, y = mouse.position
            mouse.position = (x + nx * MAX_SPEED, y - ny * MAX_SPEED)

        # 按键边沿检测
        cur = flatten(status["buttons"])
        now = time.monotonic()
        for key in cur - prev_buttons:   # 新按下
            if key not in MAPPING:
                continue
            act = MAPPING[key]
            if act[0] in HOLD_KINDS:
                # 长按型：按下立即触发 down（不防抖，靠 down/up 配对）
                print(f"按下: {key} → {act}")
                do_press(act)
                if act[0] == "hold_fn":
                    fn_held = True
            else:
                # 点击型：防抖，DEBOUNCE 秒内只触发一次
                if now - last_press.get(key, 0) >= DEBOUNCE:
                    print(f"按下: {key} → {act}")
                    do_press(act)
                    last_press[key] = now
        for key in prev_buttons - cur:   # 新松开
            if key in MAPPING and MAPPING[key][0] in HOLD_KINDS:
                print(f"松开: {key}")
                do_release(MAPPING[key])
                if MAPPING[key][0] == "hold_fn":
                    fn_held = False
        prev_buttons = cur

        time.sleep(period)


if __name__ == "__main__":
    main()
