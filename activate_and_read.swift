import Foundation
import IOKit
import IOKit.hid

/// 阶段 3 修正：手柄静默后不发 0x30，需主动发 subcommand 激活。
/// 发 0x01 output report 携带 subcommand：
///   - subcmd 0x40 (SetInputReportMode) data=[0x30] 切标准报告
///   - subcmd 0x03 (SetIMU) data=[0x01] 开 IMU（驱动活跃发送）
/// 用已验证通的 IOKit SetReport 通路。

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

func sendSubcmd(_ dev: IOHIDDevice, counter: UInt8, subcmd: UInt8, data: [UInt8]) {
    // report 0x01: [counter, rumble×8, subcmd, data...], 补到 49 字节
    var buf: [UInt8] = [counter, 0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40, subcmd]
    buf.append(contentsOf: data)
    while buf.count < 49 { buf.append(0) }
    let r = buf.withUnsafeBufferPointer { ptr -> IOReturn in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x01), ptr.baseAddress!, CFIndex(buf.count))
    }
    print("  send subcmd 0x\(String(subcmd, radix: 16)) -> \(r)")
}

// 1. 先注册 input callback（用 nil context，最简）
var frameCount = 0
func productID(_ dev: IOHIDDevice) -> UInt32 {
    return (IOHIDDeviceGetProperty(dev, "ProductID" as CFString) as? UInt32) ?? 0
}
// dev0 按键解析状态：用 UnsafeMutablePointer 持有，避开 Swift 数组独占访问问题
let dev0 = devices[0]
let pid0 = productID(dev0)
let side0 = (pid0 == 0x2006) ? "L" : "R"
let prevPtr0 = UnsafeMutablePointer<UInt8>.allocate(capacity: 1)
prevPtr0.initialize(to: 0)
let prevBytes = UnsafeMutablePointer<UInt8>.allocate(capacity: 6)
for i in 0..<6 { prevBytes[i] = 0 }
let keys0: [(Int, Int, String)] = (side0 == "L")
    ? [(3,0,"Down"),(3,1,"Up"),(3,2,"Right"),(3,3,"Left"),(3,4,"SR"),(3,5,"SL"),(3,6,"L"),(3,7,"ZL")]
    : [(3,0,"Y"),(3,1,"X"),(3,2,"B"),(3,3,"A"),(3,4,"SR"),(3,5,"SL"),(3,6,"R"),(3,7,"ZR")]
let callback: IOHIDReportCallback = { _, _, _, _, reportID, report, reportLength in
    if reportID == 0x30 {
        frameCount += 1
        // 打印完整 49 字节的前 12 字节，每 20 帧打一次
        if frameCount % 20 == 1 {
            let hex = (0..<min(12, reportLength)).map { String(format: "%02X", report[$0]) }.joined(separator: " ")
            print("[\(side0) f\(frameCount)] \(hex)")
        }
    }
}

var bufferPtrs: [UnsafeMutablePointer<UInt8>] = []
for dev in devices {
    let p = UnsafeMutablePointer<UInt8>.allocate(capacity: 362)
    p.initialize(repeating: 0, count: 362)
    bufferPtrs.append(p)
    IOHIDDeviceRegisterInputReportCallback(dev, p, 362, callback, nil)
}
IOHIDManagerScheduleWithRunLoop(manager, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)

// 2. 激活：先持续 rumble 唤醒（1秒/设备），再发 subcmd 切报告模式
func sendRumble(_ dev: IOHIDDevice, counter: UInt8, on: Bool) {
    let r: [UInt8] = on ? [0x20,0x20,0x00,0x80, 0x20,0x20,0x00,0x80]
                        : [0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40]
    var buf: [UInt8] = [counter] + r
    while buf.count < 49 { buf.append(0) }
    _ = buf.withUnsafeBufferPointer { ptr -> IOReturn in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x10), ptr.baseAddress!, CFIndex(buf.count))
    }
}
print("=== 激活：rumble 唤醒 + subcmd ===")
var counter: UInt8 = 0
for dev in devices {
    let prod = (IOHIDDeviceGetProperty(dev, "Product" as CFString) as? String) ?? "?"
    print("[\(prod)] rumble 唤醒 1 秒...")
    sendRumble(dev, counter: counter, on: true); counter &+= 1
    CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 1.0, false)  // 持续震动期间跑 runloop
    sendRumble(dev, counter: counter, on: false); counter &+= 1
    usleep(50_000)
    sendSubcmd(dev, counter: counter, subcmd: 0x40, data: [0x30]); counter &+= 1
    usleep(50_000)
    sendSubcmd(dev, counter: counter, subcmd: 0x03, data: [0x01]); counter &+= 1
    usleep(50_000)
}

// 3. 跑 runloop，每 1 秒重发 0x40 保持活跃，共 10 秒
print("\n=== 监听 10 秒（按手柄按键）===")
var tickCounter: UInt8 = counter
for i in 0..<10 {
    for dev in devices {
        sendSubcmd(dev, counter: tickCounter, subcmd: 0x40, data: [0x30])
        tickCounter &+= 1
    }
    CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 1.0, false)
    print("  [tick \(i)] 累计收到 \(frameCount) 帧 0x30")
}
print("\n=== 完成，共收到 \(frameCount) 帧 0x30 ===")
