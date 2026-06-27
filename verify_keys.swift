import Foundation
import IOKit
import IOKit.hid

/// 验证根因：用 IOKit 发正确激活序列（0x40+0x01 EnableIMU, 0x03+0x30 SetReportMode），
/// 看按键是否开始上报到 byte3-5。
/// pyjoycon 用 hidapi write 发这俩被 macOS 吞了，所以按键不上报。IOKit SetReport 能发成功。

let VENDOR: UInt32 = 0x057E
let manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(0))
IOHIDManagerSetDeviceMatching(manager, [kIOHIDVendorIDKey: VENDOR] as CFDictionary)
_ = IOHIDManagerOpen(manager, IOOptionBits(0))
guard let devSet = IOHIDManagerCopyDevices(manager) else { print("无设备"); exit(1) }
let count = CFSetGetCount(devSet)
var raw = [UnsafeRawPointer?](repeating: nil, count: count)
CFSetGetValues(devSet, &raw)
let devices = raw.compactMap { $0 }.map { unsafeBitCast($0, to: IOHIDDevice.self) }

var pkt: UInt8 = 0
func subcmd(_ dev: IOHIDDevice, _ sc: UInt8, _ arg: UInt8) {
    // 0x01 output: [counter, rumble×8, subcmd, arg]
    var buf: [UInt8] = [pkt, 0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40, sc, arg]
    while buf.count < 49 { buf.append(0) }
    pkt = pkt &+ 1
    _ = buf.withUnsafeBufferPointer { p in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x01), p.baseAddress!, CFIndex(buf.count))
    }
}

// 边沿检测状态
let prev = UnsafeMutablePointer<UInt8>.allocate(capacity: 3)
prev.initialize(repeating: 0, count: 3)
var maxNonzero = 0
let callback: IOHIDReportCallback = { _, _, _, _, rid, report, len in
    guard rid == 0x30, len >= 6 else { return }
    let b3 = Int(report[3]), b4 = Int(report[4]), b5 = Int(report[5])
    if b3 != 0 || b4 != 0 || b5 != 0 {
        print("  >>> 按键! byte3-5 = \(String(format:"%02X",b3)) \(String(format:"%02X",b4)) \(String(format:"%02X",b5))")
        maxNonzero += 1
    }
}

let p = UnsafeMutablePointer<UInt8>.allocate(capacity: 362)
p.initialize(repeating: 0, count: 362)
for dev in devices {
    IOHIDDeviceRegisterInputReportCallback(dev, p, 362, callback, nil)
}
IOHIDManagerScheduleWithRunLoop(manager, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)

print("=== 用 IOKit 发正确激活序列 ===")
for dev in devices {
    subcmd(dev, 0x40, 0x01)  // Enable IMU
    usleep(30_000)
    subcmd(dev, 0x03, 0x30)  // Set input report mode = 0x30
    usleep(30_000)
}
print("激活完成。请反复按手柄按键 10 秒（A/B/R/+ 等）...")

// 监听 10 秒，每秒重发激活保持
for _ in 0..<10 {
    for dev in devices {
        subcmd(dev, 0x03, 0x30)
    }
    CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 1.0, false)
}
print("=== 结束。检测到 \(maxNonzero) 次非零按键 ===")
