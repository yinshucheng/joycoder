#!/usr/bin/env python3
"""阶段 2 happy-path：验证 IOKit IOHIDDeviceSetReport 能否驱动 Joy-Con。

判据（binary）：用 IOHIDDeviceSetReport 发 Set Player Lights subcommand (0x04)，
LED 灯亮 = IOKit write 通路打通，subcommand 路线可行。
灯不亮 = IOKit Set-Report 对 Joy-Con 也无效，需上 Swift 原生或止损。

与 hidapi 的关键区别：IOHIDDeviceSetReport 的 reportID 单独传参，
buffer 不含 report-id 前缀（hidapi write 要带前缀）。

用 ctypes 直接调 IOKit/CoreFoundation C API，零额外依赖。
"""
import ctypes
import ctypes.util
import time

# ---- 加载框架 ----
CF = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
IOKit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")

# ---- 类型 ----
CFTypeRef = ctypes.c_void_p
CFAllocatorRef = ctypes.c_void_p
CFStringRef = ctypes.c_void_p
CFMutableDictionaryRef = ctypes.c_void_p
IOHIDManagerRef = ctypes.c_void_p
IOHIDDeviceRef = ctypes.c_void_p
CFSetRef = ctypes.c_void_p
CFIndex = ctypes.c_long
IOOptionBits = ctypes.c_uint32

kIOHIDReportTypeOutput = 1
kIOHIDManagerOptionNone = 0

# ---- CF 辅助：构造 CFString / CFNumber / CFDictionary ----
def cf_string(s):
    """Python str -> CFStringRef（ASCII）。"""
    return CF.CFStringCreateWithCString(None, s.encode("ascii"), 0)

def cf_number_uint32(val):
    """uint32 -> CFNumberRef。"""
    n = ctypes.c_uint32(val)
    return CF.CFNumberCreate(None, 1, ctypes.byref(n))  # type=1 = kCFNumberSInt32Type

def main():
    VENDOR = 0x057E
    # 两个 Joy-Con 都是 0x2006（L）
    PRODUCTS = [0x2006]

    # 1. 创建 IOHIDManager
    IOKit.IOHIDManagerCreate.argtypes = [CFAllocatorRef, IOOptionBits]
    IOKit.IOHIDManagerCreate.restype = IOHIDManagerRef
    mgr = IOKit.IOHIDManagerCreate(None, kIOHIDManagerOptionNone)
    if not mgr:
        print("!! IOHIDManagerCreate 失败")
        return

    # 2. 匹配任天堂 vendor（用 vendor 单字段匹配，覆盖两个产品）
    CF.CFDictionaryCreateMutable.argtypes = [CFAllocatorRef, CFIndex, ctypes.c_void_p, ctypes.c_void_p]
    CF.CFDictionaryCreateMutable.restype = CFMutableDictionaryRef
    match = CF.CFDictionaryCreateMutable(None, 0, None, None)
    k = cf_string("VendorID"); v = cf_number_uint32(VENDOR)
    CF.CFDictionarySetValue.argtypes = [CFMutableDictionaryRef, CFTypeRef, CFTypeRef]
    CF.CFDictionarySetValue(match, k, v)

    IOKit.IOHIDManagerSetDeviceMatching.argtypes = [IOHIDManagerRef, CFMutableDictionaryRef]
    IOKit.IOHIDManagerSetDeviceMatching(mgr, match)

    # 3. 打开 manager
    IOKit.IOHIDManagerOpen.argtypes = [IOHIDManagerRef, IOOptionBits]
    IOKit.IOHIDManagerOpen.restype = ctypes.c_int32
    rc = IOKit.IOHIDManagerOpen(mgr, kIOHIDManagerOptionNone)
    print(f"IOHIDManagerOpen -> {rc} (0=成功)")
    if rc != 0:
        print("!! 打开 manager 失败")
        return

    # 4. 拿到设备集合
    IOKit.IOHIDManagerCopyDevices.argtypes = [IOHIDManagerRef]
    IOKit.IOHIDManagerCopyDevices.restype = CFSetRef
    dev_set = IOKit.IOHIDManagerCopyDevices(mgr)
    if not dev_set:
        print("!! 没有匹配的 HID 设备")
        return

    CF.CFSetGetCount.argtypes = [CFSetRef]
    CF.CFSetGetCount.restype = CFIndex
    count = CF.CFSetGetCount(dev_set)
    print(f"匹配到 {count} 个 HID 设备")

    # 取出设备引用数组
    CF.CFSetGetValues.argtypes = [CFSetRef, ctypes.POINTER(IOHIDDeviceRef)]
    devs = (IOHIDDeviceRef * count)()
    CF.CFSetGetValues(dev_set, devs)

    # 5. 对每个设备发 LED subcommand
    # Joy-Con output report 0x01: [counter, rumble×8, subcmd_id, data...]
    # buffer 不含 report-id（reportID=0x01 单独传给 SetReport）
    for idx in range(count):
        dev = devs[idx]
        # 读 product string 辅助辨认
        IOKit.IOHIDDeviceGetProperty.argtypes = [IOHIDDeviceRef, CFStringRef]
        IOKit.IOHIDDeviceGetProperty.restype = CFTypeRef
        prod_ref = IOKit.IOHIDDeviceGetProperty(dev, cf_string("Product"))
        # 简化：不解析 CFString，直接打印指针
        print(f"\n--- 设备 #{idx} (ptr={dev}) ---")

        IOKit.IOHIDDeviceSetReport.argtypes = [IOHIDDeviceRef, ctypes.c_uint32,
                                                ctypes.c_uint32, ctypes.c_char_p, CFIndex]
        IOKit.IOHIDDeviceSetReport.restype = CFIndex

        for counter in range(4):
            # 构造 49 字节 output buffer（去掉 report-id 后的长度）
            buf = bytearray(49)
            buf[0] = counter & 0xFF          # global packet counter
            # buf[1..8] rumble = 0
            buf[9] = 0x04                     # subcmd: Set Player Lights
            buf[10] = 0x0F                    # 全部 4 颗 LED 亮
            cbuf = ctypes.c_char_p(bytes(buf))
            n = IOKit.IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, 0x01, cbuf, len(buf))
            print(f"  SetReport counter={counter} -> 返回 {n} (>=0=成功)")
            time.sleep(0.15)

    print("\n>> 现在观察 Joy-Con LED 灯是否变化（3 秒）...")
    time.sleep(3)
    print("==== 判据 ====")
    print("LED 变化（有灯新亮/全亮 4 颗）→ IOKit Set-Report 通路 OK，进阶段 3。")
    print("灯无变化 → IOKit Set-Report 对 Joy-Con 也无效，需上 Swift 原生或止损。")


if __name__ == "__main__":
    main()
