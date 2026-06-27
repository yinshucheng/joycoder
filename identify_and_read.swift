import Foundation
import IOKit
import IOKit.hid

/// 阶段 2 收尾：① 逐个震动辨认手柄；② 验证 input 通路（读按键报告）。

let VENDOR: UInt32 = 0x057E

let manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(0))
let match: CFDictionary = [kIOHIDVendorIDKey: VENDOR] as CFDictionary
IOHIDManagerSetDeviceMatching(manager, match)
_ = IOHIDManagerOpen(manager, IOOptionBits(0))
guard let devSet = IOHIDManagerCopyDevices(manager) else { print("!! 无设备"); exit(1) }
let count = CFSetGetCount(devSet)
var raw = [UnsafeRawPointer?](repeating: nil, count: count)
CFSetGetValues(devSet, &raw)
let devices: [IOHIDDevice] = raw.compactMap { $0 }.map { unsafeBitCast($0, to: IOHIDDevice.self) }

func rumbleOn(_ dev: IOHIDDevice, counter: UInt8) {
    var buf: [UInt8] = [counter, 0x20,0x20,0x00,0x80, 0x20,0x20,0x00,0x80]
    while buf.count < 49 { buf.append(0) }
    _ = buf.withUnsafeBufferPointer { ptr -> IOReturn in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x10), ptr.baseAddress!, CFIndex(buf.count))
    }
}
func rumbleStop(_ dev: IOHIDDevice, counter: UInt8) {
    var buf: [UInt8] = [counter, 0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40]
    while buf.count < 49 { buf.append(0) }
    _ = buf.withUnsafeBufferPointer { ptr -> IOReturn in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x10), ptr.baseAddress!, CFIndex(buf.count))
    }
}

// === 第1部分：逐个震动辨认 ===
print("=== 第1部分：逐个震动辨认（每个震1秒，间隔1秒）===")
print("请记住哪个手柄在哪个顺序震动\n")
for (idx, dev) in devices.enumerated() {
    let prod = (IOHIDDeviceGetProperty(dev, "Product" as CFString) as? String) ?? "?"
    print("[\(idx)] \(prod) 开始震动...")
    rumbleOn(dev, counter: UInt8(idx))
    sleep(1)
    rumbleStop(dev, counter: UInt8(idx))
    print("[\(idx)] 停止，间隔1秒")
    sleep(1)
}

// === 第2部分：尝试读 input 报告 ===
// macOS IOHIDManager 对蓝牙 HID device 的 read：用 IOHIDDeviceOpen 后注册 input callback，
// 或直接读。这里先试同步读，看能否拿到数据。
print("\n=== 第2部分：读 input 报告 ===")
print("现在请随便按手柄按键，持续 4 秒...")

// 注册 input report callback
class ReadState {
    var packets: [(Int, [UInt8])] = []
}
let state = ReadState()

let callback: IOHIDReportCallback = { _, _, _, reportType, reportID, report, reportLength in
    var data = [UInt8](repeating: 0, count: reportLength)
    for i in 0..<reportLength { data[i] = report[i] }
    print("  收到 input: reportID=0x\(String(reportID, radix: 16)) len=\(reportLength) "
          + "前12字节: \(data.prefix(12).map { String(format: "%02X", $0) }.joined(separator: " "))")
}

// 每个设备分配一个 input buffer（IOHIDDeviceRegisterInputReportCallback 需要）
// buffer 必须在 runloop 期间一直存活，用 UnsafeMutablePointer 持有
var bufferPtrs: [UnsafeMutablePointer<UInt8>] = []
for dev in devices {
    let p = UnsafeMutablePointer<UInt8>.allocate(capacity: 362)
    p.initialize(repeating: 0, count: 362)
    bufferPtrs.append(p)
    IOHIDDeviceRegisterInputReportCallback(dev, p, 362, callback, nil)
}
// 需要一个 runloop 让 callback 触发
IOHIDManagerScheduleWithRunLoop(manager, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)

print("（监听 4 秒，期间按手柄按键）")
CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 4.0, false)

print("\n=== 完成 ===")
print("如果上面有'收到 input'行 → 读通路通，进阶段3解析按键")
print("如果完全没有 → 读还需 subcommand 切标准模式，或换 callback 方式")
