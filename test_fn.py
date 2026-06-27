#!/usr/bin/env python3
"""测试能否用 CGEvent 模拟 Fn 键，唤起豆包语音输入。

macOS 的 Fn 键是特殊修饰键，不是普通键码。
尝试多种方式发 Fn，看哪种能触发豆包。
"""
import time
import Quartz

# Fn 键的虚拟键码（kVK_Function = 0x3F = 63）
FN_KEYCODE = 0x3F

print("3 秒后开始测试模拟 Fn 键，请观察豆包语音输入是否被唤起...")
time.sleep(3)

# 方式 1：用 NSEvent flags 发 Fn 修饰键的 keyDown/keyUp
def send_fn_via_flags():
    print("方式1: CGEvent keyDown/keyUp with Fn keycode + secondaryFn flag")
    # keyDown
    ev_down = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, True)
    Quartz.CGEventSetFlags(ev_down, Quartz.kCGEventFlagMaskSecondaryFn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_down)
    time.sleep(0.05)
    # keyUp
    ev_up = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, False)
    Quartz.CGEventSetFlags(ev_up, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_up)

# 方式 2：只发 flagsChanged（Fn 作为修饰键的标准事件）
def send_fn_flags_changed():
    print("方式2: 发 secondaryFn flag 变化（模拟按下再松开）")
    # 按下：设置 Fn flag
    ev = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, True)
    Quartz.CGEventSetType(ev, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskSecondaryFn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    time.sleep(0.1)
    # 松开：清除 flag
    ev2 = Quartz.CGEventCreateKeyboardEvent(None, FN_KEYCODE, False)
    Quartz.CGEventSetType(ev2, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev2, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev2)

print("\n--- 测试方式 1 ---")
send_fn_via_flags()
time.sleep(2)

print("\n--- 测试方式 2（双击 Fn）---")
send_fn_flags_changed()
time.sleep(0.2)
send_fn_flags_changed()
time.sleep(2)

print("\n--- 测试方式 2（单次）---")
send_fn_flags_changed()
time.sleep(2)

print("\n测试完成。豆包有没有被唤起？哪种方式有效？")
