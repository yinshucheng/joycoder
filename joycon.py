#!/usr/bin/env python3
"""Joy-Con 控鼠标 + 按键 DIY 映射（语音编程辅助）。

右摇杆 → 鼠标移动；面板按键 → 可配置动作（点击/回车/删除/快捷键）。

运行：
  DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/hidapi/0.15.0/lib .venv312/bin/python joycon.py

需 macOS 辅助功能权限（系统设置→隐私与安全性→辅助功能，给终端授权）。
"""
import time
import threading
from pyjoycon import JoyCon
from pyjoycon.constants import (
    JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID, JOYCON_L_PRODUCT_ID,
)
from pynput.mouse import Controller as MouseCtl, Button
from pynput.keyboard import Controller as KeyCtl, Key
import Quartz

# pyjoycon 的后台读线程(_update_input_report)在 macOS 蓝牙抖动时会偶发
# HIDException 崩溃，默认会把一大坨 traceback 打到屏幕。这是预期内的老毛病
# ——主循环的活性检测会自动重连。这里拦掉这个吓人的堆栈，只留一行提示；
# 其他未预期的线程异常仍照常完整打印（不掩盖真问题）。
_default_excepthook = threading.excepthook

def _quiet_thread_excepthook(args):
    # 只认 HIDException（手柄读失败）——它只可能来自 pyjoycon 的后台读线程。
    if args.exc_type is not None and args.exc_type.__name__ == "HIDException":
        print("（手柄读取中断，正在自动重连…）", flush=True)
        return
    _default_excepthook(args)   # 其他异常照常完整打印

threading.excepthook = _quiet_thread_excepthook

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


# ============== 鼠标移动（用 Quartz，不依赖 pynput 读坐标）==============
# 为何不用 pynput 的 mouse.position 读-改-写：实测某些环境（多屏遗留/坐标系
# 错乱）下它读回的 y 是垃圾值（如 20055，远超屏高），导致光标卡死在边缘无法
# 上下。改为自维护坐标 + 每帧 clamp 到所有显示器的联合范围，绝对定位。

def _screen_bounds():
    """所有活动显示器的联合包围盒 (minx, miny, maxx, maxy)。"""
    err, ids, cnt = Quartz.CGGetActiveDisplayList(16, None, None)
    if err or not cnt:
        b = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
        return (b.origin.x, b.origin.y,
                b.origin.x + b.size.width, b.origin.y + b.size.height)
    minx = miny = float("inf"); maxx = maxy = float("-inf")
    for d in ids[:cnt]:
        b = Quartz.CGDisplayBounds(d)
        minx = min(minx, b.origin.x); miny = min(miny, b.origin.y)
        maxx = max(maxx, b.origin.x + b.size.width)
        maxy = max(maxy, b.origin.y + b.size.height)
    return (minx, miny, maxx, maxy)


def warp_mouse(x, y):
    """把光标移到绝对坐标 (x, y)。用 CGEvent 发移动事件，比写 mouse.position 可靠。"""
    pos = Quartz.CGPointMake(x, y)
    ev = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventMouseMoved, pos, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def read_mouse(bounds):
    """读系统真实光标位置（CGEvent，非 pynput）。落在屏幕范围内才返回，否则 None。"""
    loc = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    minx, miny, maxx, maxy = bounds
    if minx <= loc.x <= maxx and miny <= loc.y <= maxy:
        return loc.x, loc.y
    return None


# ============== 配置区（DIY 改这里）==============

# 通用手感参数（左右手柄共用）
DEADZONE = 0.22      # 死区（防漂移/防飘，调大更稳）
MAX_SPEED = 11.0     # 满推时每帧移动像素（调小，防太快）
POLL_HZ = 120
DEBOUNCE = 0.30      # 点击型按键防抖窗口（秒）：按一下只触发一次，防抖动连发

# 动作类型（MAPPING 的值）：
# 边沿触发型（按下瞬间执行一次）：
#   ("click", Button.left)          鼠标左键点击
#   ("click", Button.right)         鼠标右键点击
#   ("key", Key.enter)              按一个键
#   ("key", Key.backspace)          删除
#   ("combo", [Key.cmd, 'c'])       组合键 Cmd+C
#   ("shell", "command")            执行 shell 命令
# 长按型（按住=按下，松开=松开）：
#   ("hold_fn",)                    长按 Fn（豆包语音：按住说话，松开结束）

# Profile：每只手柄一套。自动检测连的是左还是右后加载对应 profile。
#   stick     摇杆用哪侧（"left" / "right"），对应 analog-sticks 里的键
#   cal       摇杆标定 (中心, 最小, 最大)，h/v 各一组（实测值）
#   mapping   基础按键映射（所有模式共用）。键名形如 "<组>.<键>"
#
# 可选：多模式（Plus 等键切换）。不写这几个字段 = 单模式（摇杆控鼠标）。
#   switch_key  切换模式的按键名（如 "shared.plus"）
#   modes       模式列表，每个 = {"name","stick","mapping"}：
#                 stick    该模式摇杆行为："mouse"(控鼠标) / "dpad"(推动=方向键)
#                 mapping  该模式额外/覆盖的按键映射（与基础 mapping 合并）
# 左手柄键：left.up/down/left/right left.l left.zl  shared.minus shared.capture
# 右手柄可用键（实测）：right.a/b/x/y right.r right.zr right.sl right.sr
#                       shared.plus shared.home（r-stick 摇杆按下读得到但不稳，不用）
PROFILES = {
    "right": {
        "stick": "right",
        "cal": {"h": (2101, 741, 3461), "v": (1884, 783, 2986)},
        # 基础映射：所有模式一致（含义不随模式变，避免记混）。
        # 唯一的例外是 A 键，随模式变（见 modes）：鼠标模式=左键，方向模式=空格。
        "mapping": {
            "right.zr":  ("hold_fn",),              # ZR 扳机 = 长按说话 ★
            "right.y":   ("hold_fn",),              # Y = 长按说话（比肩键顺手）★
            "right.b":   ("key", Key.enter),        # B = 回车
            "right.x":   ("key", Key.backspace),    # X = 删除
            "right.r":   ("click", Button.left),    # R = 左键点击（肩键，备用）
            "right.sl":  ("key", ","),              # SL 内侧键 = 逗号
            "right.sr":  ("key", Key.esc),          # SR 内侧键 = Esc 取消/中断
        },
        "switch_key": "shared.plus",                # Plus = 切换摇杆模式
        "modes": [
            # 鼠标模式：摇杆控光标，A = 左键点击（拇指最顺手的点击键）
            {"name": "🖱️ 鼠标模式", "stick": "mouse",
             "mapping": {"right.a": ("click", Button.left)}},
            # 方向模式：摇杆推动发 ↑↓←→，A = 空格
            {"name": "⬆️ 方向模式", "stick": "dpad",
             "mapping": {"right.a": ("key", Key.space)}},
        ],
    },
    "left": {
        "stick": "left",
        # 实测：静止 h≈2005 v≈2304；推满 h 532~3307 v 1228~3495
        "cal": {"h": (2005, 532, 3307), "v": (2304, 1228, 3495)},
        "mapping": {
            "left.zl":     ("hold_fn",),              # ZL 扳机 = 长按说话（对齐右 ZR）★
            "left.up":     ("key", Key.enter),        # ↑ = 回车（对齐右 B）
            "left.down":   ("key", Key.backspace),    # ↓ = 删除（对齐右 X）
            "left.left":   ("click", Button.left),    # ← = 左键点击（对齐右 A）
            "left.right":  ("click", Button.right),   # → = 右键点击（对齐右 Y）
        },
    },
}

# ===============================================

mouse = MouseCtl()
kb = KeyCtl()


def norm(raw, cal):
    center, lo, hi = cal
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

# 方向模式：摇杆推过此阈值算一次方向（归一化后绝对值），低于则视为回中
DPAD_THRESHOLD = 0.5
DPAD_REPEAT = 0.18    # 持续推住时方向键的连发间隔（秒）


def stick_direction(nx, ny):
    """摇杆归一化坐标 → 方向键，或 None（回中/未过阈值）。取主轴，斜推按更大的轴。"""
    if abs(nx) < DPAD_THRESHOLD and abs(ny) < DPAD_THRESHOLD:
        return None
    if abs(nx) >= abs(ny):
        return Key.right if nx > 0 else Key.left
    return Key.up if ny > 0 else Key.down


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


# 产品 ID → 手柄侧（profile 名）。检测连的是哪只就加载对应 profile。
SIDE_BY_PID = {
    JOYCON_R_PRODUCT_ID: "right",
    JOYCON_L_PRODUCT_ID: "left",
}


def connect():
    """等手柄出现并连上，自动识别左/右。返回 (jc, side)。

    左右都连着时优先用右（保持老行为）。手柄没开/没连时持续等待，不崩溃。
    """
    from pyjoycon.device import get_device_ids
    waited = False
    while True:
        present = {i[1] for i in get_device_ids() if i[1] in SIDE_BY_PID}
        # 左右都在时优先右手柄，行为与单右手柄时一致
        for pid in (JOYCON_R_PRODUCT_ID, JOYCON_L_PRODUCT_ID):
            if pid not in present:
                continue
            side = SIDE_BY_PID[pid]
            try:
                jc = JoyCon(JOYCON_VENDOR_ID, pid)
                print(f"✓ 手柄已连接（{side} Joy-Con）")
                return jc, side
            except Exception as e:
                print(f"连接失败（{side}），重试: {e}")
        if not waited:
            print("等待手柄连接...（蓝牙连上左/右 Joy-Con）", flush=True)
            waited = True
        time.sleep(2)


def main():
    print("Joy-Con 控制已启动。")

    jc, side = connect()
    profile = PROFILES[side]
    prev_buttons = set()
    last_press = {}     # key -> 上次触发按下的时间戳（防抖）
    fn_held = False     # Fn 是否被按住（断线安全）
    period = 1.0 / POLL_HZ
    last_timer = -1     # 上次的 timer 字节（活性检测）
    stale = 0           # timer 连续不变的帧数
    mode_idx = 0        # 当前模式下标（多模式 profile 用）
    last_dpad = 0.0     # 方向模式：上次发方向键的时间戳（连发节流）
    prev_dir = None     # 方向模式：上一帧的方向（回中后才能再次触发）

    # 自维护鼠标坐标：初始放屏幕中心（不读 pynput 的坏坐标），之后累积+clamp
    sb = _screen_bounds()
    mx = (sb[0] + sb[2]) / 2
    my = (sb[1] + sb[3]) / 2

    def modes():
        """当前 profile 的模式列表；单模式 profile 合成一个默认模式。"""
        return profile.get("modes") or [
            {"name": "🖱️ 鼠标模式", "stick": "mouse", "mapping": {}}
        ]

    def cur_mode():
        return modes()[mode_idx % len(modes())]

    def cur_mapping():
        """基础映射 + 当前模式映射（模式覆盖基础）。"""
        m = dict(profile.get("mapping", {}))
        m.update(cur_mode().get("mapping", {}))
        return m

    def announce():
        mode = cur_mode()
        stick_desc = "移动鼠标" if mode["stick"] == "mouse" else "推动=方向键 ↑↓←→"
        print(f"【{mode['name']}】 {profile['stick']} 摇杆 → {stick_desc}")
        for key, act in cur_mapping().items():
            print(f"  {key} → {act}")
        if profile.get("switch_key"):
            print(f"  {profile['switch_key']} → 切换模式")
        print("Ctrl+C 退出。\n")

    announce()

    def reconnect(reason):
        # 重连时重新检测左/右，允许中途换手柄
        nonlocal jc, side, profile, prev_buttons, fn_held, last_timer, stale
        nonlocal mode_idx, last_dpad, prev_dir
        print(f"⚠️ 手柄断线（{reason}），重连中...")
        if fn_held:
            fn_up(); fn_held = False
            print("  （已安全松开 Fn）")
        prev_buttons = set()
        last_timer = -1; stale = 0
        mode_idx = 0; last_dpad = 0.0; prev_dir = None
        try:
            jc._close()      # 释放旧连接，避免"device already open"
        except Exception:
            pass
        time.sleep(0.5)
        jc, new_side = connect()
        if new_side != side:
            side = new_side
            profile = PROFILES[side]
            print(f"  （已切换到 {side} Joy-Con 配置）")
            announce()

    while True:
        # 读状态；pyjoycon 后台读线程崩溃时 get_status 不抛异常但 timer 卡住
        try:
            status = jc.get_status()
            # 活性检测：timer(byte1) 应每帧变化，卡住 = 后台线程死了
            t = jc._input_report[1]
            if t == last_timer:
                stale += 1
                if stale > POLL_HZ:   # 约 1 秒没更新 → 判定断线
                    reconnect("数据停止更新")
                    continue
            else:
                stale = 0
                last_timer = t
        except Exception as e:
            reconnect(str(e))
            continue

        now = time.monotonic()

        # 摇杆：按当前模式分流（控鼠标 / 当方向键）
        s = status["analog-sticks"][profile["stick"]]
        cal = profile["cal"]
        nx = norm(s["horizontal"], cal["h"])
        ny = norm(s["vertical"], cal["v"])
        if cur_mode()["stick"] == "dpad":
            # 方向模式：推过阈值发一次方向键；推住则按 DPAD_REPEAT 连发；回中可再触发
            d = stick_direction(nx, ny)
            if d is None:
                prev_dir = None
            elif d != prev_dir or now - last_dpad >= DPAD_REPEAT:
                kb.press(d); kb.release(d)
                prev_dir = d
                last_dpad = now
        else:
            # 鼠标模式：累积到自维护坐标并 clamp 到屏幕范围，再绝对定位
            if nx or ny:
                bounds = _screen_bounds()
                # 以系统真实光标为基准（若有效），这样和触摸板移动能协同
                real = read_mouse(bounds)
                if real:
                    mx, my = real
                minx, miny, maxx, maxy = bounds
                mx = min(maxx - 1, max(minx, mx + nx * MAX_SPEED))
                my = min(maxy - 1, max(miny, my - ny * MAX_SPEED))
                warp_mouse(mx, my)

        # 按键边沿检测
        mapping = cur_mapping()
        switch_key = profile.get("switch_key")
        cur = flatten(status["buttons"])
        for key in cur - prev_buttons:   # 新按下
            # 模式切换键：防抖一下，切换并重置方向状态
            if key == switch_key:
                if now - last_press.get(key, 0) >= DEBOUNCE:
                    mode_idx = (mode_idx + 1) % len(modes())
                    prev_dir = None; last_dpad = 0.0
                    last_press[key] = now
                    print(f"\n切换 → 【{cur_mode()['name']}】")
                    announce()
                continue
            if key not in mapping:
                continue
            act = mapping[key]
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
            if key in mapping and mapping[key][0] in HOLD_KINDS:
                print(f"松开: {key}")
                do_release(mapping[key])
                if mapping[key][0] == "hold_fn":
                    fn_held = False
        prev_buttons = cur

        time.sleep(period)


if __name__ == "__main__":
    main()
