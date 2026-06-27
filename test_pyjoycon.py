#!/usr/bin/env python3
"""用 pyjoycon get_status() 读按键（vibejoy 同款用法），验证底层链路。"""
import time
from pyjoycon import JoyCon
from pyjoycon.constants import JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID

jc = JoyCon(JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID, serial="74:F9:CA:6B:2D:36")
print("已打开 Joy-Con (R)，监听 10 秒，请按 A/B/X/Y 等按键...")

prev = None
for i in range(200):  # 每 0.05s 轮询，共 10 秒
    try:
        s = jc.get_status()
    except Exception as e:
        print(f"读取异常: {e}"); break
    buttons = s.get("buttons", {})
    # 右手柄按键在 buttons dict 里
    cur = {k: v for k, v in buttons.items() if v}
    if cur != prev:
        print(f"[{i}] 按下: {sorted(cur.keys()) if cur else '（无）'}  完整buttons={buttons}")
        prev = cur
    time.sleep(0.05)
print("结束")
