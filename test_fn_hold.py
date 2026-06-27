#!/usr/bin/env python3
"""测试长按 Fn：按下 Fn 保持 3 秒（期间说话），再松开。
对应豆包"长按 Fn 持续输入"的交互。"""
import time
import Quartz

FN_KEYCODE = 0x3F

def fn_down():
    ev = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, True)
    Quartz.CGEventSetType(ev, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskSecondaryFn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def fn_up():
    ev = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, False)
    Quartz.CGEventSetType(ev, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

print("5 秒后开始长按 Fn（保持 8 秒）。请现在就把光标点到输入框，准备说话...")
for s in range(5, 0, -1):
    print(f"  {s}...", flush=True)
    time.sleep(1)
print(">>> Fn 按下！现在对麦克风说话（持续 8 秒）...", flush=True)
fn_down()
for s in range(8, 0, -1):
    print(f"  说话中 {s}", flush=True)
    time.sleep(1)
fn_up()
print(">>> Fn 松开。豆包有没有听写出文字？", flush=True)
