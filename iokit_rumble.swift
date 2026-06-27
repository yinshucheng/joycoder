import Foundation
import IOKit
import IOKit.hid

/// 阶段 2 重新验证：用标准 rumble neutral 值 + 正确 subcommand 格式，
/// 同时尝试 rumble 震动（report 0x10）和 LED（subcmd 0x04）。
/// 判据：手柄震动 或 LED 变化 = 通路通；都没有 = control transfer 通道无效，止损。

let VENDOR: UInt32 = 0x057E

let manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(0))
let match: CFDictionary = [kIOHIDVendorIDKey: VENDOR] as CFDictionary
IOHIDManagerSetDeviceMatching(manager, match)
let openRC = IOHIDManagerOpen(manager, IOOptionBits(0))
print("IOHIDManagerOpen -> \(openRC)")
if openRC != 0 { print("!! 打开失败"); exit(1) }

guard let devSet = IOHIDManagerCopyDevices(manager) else { print("!! 无设备"); exit(1) }
let count = CFSetGetCount(devSet)
var raw = [UnsafeRawPointer?](repeating: nil, count: count)
CFSetGetValues(devSet, &raw)
let devices: [IOHIDDevice] = raw.compactMap { $0 }.map { unsafeBitCast($0, to: IOHIDDevice.self) }

// 标准 rumble neutral 值（左+右各4字节，社区验证过）
// 0x00,0x01,0x40,0x40 = 停止震动；要震动用 0x20,0x20,0x00,0x60 之类
func rumbleStop() -> [UInt8] { return [0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40] }
func rumbleOn() -> [UInt8] { return [0x20,0x20,0x00,0x80, 0x20,0x20,0x00,0x80] }

func sendSubcommand(_ dev: IOHIDDevice, counter: UInt8, subcmd: UInt8, data: [UInt8], rumble: [UInt8]) -> IOReturn {
    // output report 0x01: [counter, rumble×8, subcmd_id, data...]
    var buf: [UInt8] = []
    buf.append(counter)
    buf.append(contentsOf: rumble)
    buf.append(subcmd)
    buf.append(contentsOf: data)
    // 补齐到 49 字节（output report 固定长度）
    while buf.count < 49 { buf.append(0) }
    return buf.withUnsafeBufferPointer { ptr -> IOReturn in
        return IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x01), ptr.baseAddress!, CFIndex(buf.count))
    }
}

for (idx, dev) in devices.enumerated() {
    let prod = (IOHIDDeviceGetProperty(dev, "Product" as CFString) as? String) ?? "?"
    print("\n--- 设备 #\(idx): \(prod) ---")

    // 测试1：纯震动（不需要 subcommand，report 0x10 = rumble only）
    // report 0x10: [counter, rumble×8]
    var rumbleBuf: [UInt8] = [0]
    rumbleBuf.append(contentsOf: rumbleOn())
    while rumbleBuf.count < 49 { rumbleBuf.append(0) }
    let r1 = rumbleBuf.withUnsafeBufferPointer { ptr -> IOReturn in
        return IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x10), ptr.baseAddress!, CFIndex(rumbleBuf.count))
    }
    print("  [测1] rumble-only report 0x10 (震动) -> \(r1)")
    usleep(800_000)  // 震 0.8 秒

    // 停震
    var stopBuf: [UInt8] = [1]
    stopBuf.append(contentsOf: rumbleStop())
    while stopBuf.count < 49 { stopBuf.append(0) }
    let r1b = stopBuf.withUnsafeBufferPointer { ptr -> IOReturn in
        return IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x10), ptr.baseAddress!, CFIndex(stopBuf.count))
    }
    print("  [测1停] rumble stop -> \(r1b)")
    usleep(200_000)

    // 测试2：LED subcmd 0x04，带正确 rumble neutral
    for c in 0..<3 {
        let r = sendSubcommand(dev, counter: UInt8(c), subcmd: 0x04, data: [0x0F], rumble: rumbleStop())
        print("  [测2] subcmd 0x04 LED全亮 counter=\(c) -> \(r)")
        usleep(150_000)
    }
}

print("\n>> 观察（3秒）：手柄是否震动过？LED 是否变化？")
sleep(3)
print("判据：震动 或 LED变化 → 通路通；都无 → 控制传输通道无效，止损换方案")
