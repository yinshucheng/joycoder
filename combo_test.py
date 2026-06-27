#!/usr/bin/env python3
"""最终验证：pyjoycon 读（稳定）+ subprocess 调 IOKit Swift 发正确激活 subcommand。
看按键是否上报到 byte3-5。"""
import time
import subprocess
import threading
from pyjoycon import JoyCon
from pyjoycon.constants import JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID

jc = JoyCon(JOYCON_VENDOR_ID, JOYCON_R_PRODUCT_ID)
print("pyjoycon 已激活并在后台读取。")

# 后台用 IOKit 发激活 subcommand（独立进程，不抢占读）
def send_activation():
    time.sleep(0.5)
    subprocess.run(["./verify_keys"], timeout=3, capture_output=True)

# 监听 byte3-5 变化
print("请反复按手柄按键 12 秒（A/B/R/+ 等）...", flush=True)
detected = set()
t0 = time.time()
n = 0
while time.time() - t0 < 12:
    r = jc._input_report
    if r[0] == 0x30:
        n += 1
        key = (r[3], r[4], r[5])
        if key != (0, 0, 0):
            print(f"  >>> 按键! byte3-5 = {r[3]:02X} {r[4]:02X} {r[5]:02X}", flush=True)
            detected.add(key)
    time.sleep(0.02)
print(f"结束。0x30 样本 {n}，检测到 {len(detected)} 种非零按键")
