import Foundation
import IOKit
import IOKit.hid

/// 阶段 2 happy-path（Swift 版）：验证 IOKit IOHIDDeviceSetReport 能驱动 Joy-Con。
/// 判据：发 Set Player Lights subcommand (0x04) 后 LED 灯亮 = 通路打通。

let VENDOR: UInt32 = 0x057E

// 1. 创建 IOHIDManager
let manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(0))

// 2. 匹配字典：VendorID
let match: CFDictionary = [kIOHIDVendorIDKey: VENDOR] as CFDictionary
IOHIDManagerSetDeviceMatching(manager, match)

// 3. 打开
let openRC = IOHIDManagerOpen(manager, IOOptionBits(0))
print("IOHIDManagerOpen -> \(openRC) (0=成功)")
if openRC != 0 {
    print("!! 打开 manager 失败")
    exit(1)
}

// 4. 拿设备集合
guard let devSet = IOHIDManagerCopyDevices(manager) else {
    print("!! 没有匹配的 HID 设备")
    exit(1)
}
let count = CFSetGetCount(devSet)
print("匹配到 \(count) 个 HID 设备")

var rawDevices = [UnsafeRawPointer?](repeating: nil, count: count)
CFSetGetValues(devSet, &rawDevices)
let devices: [IOHIDDevice] = rawDevices.compactMap { $0 }.map { unsafeBitCast($0, to: IOHIDDevice.self) }

// 5. 对每个设备发 LED subcommand
// Joy-Con output report 0x01 buffer（不含 report-id，reportID 单独传）：
// [counter, rumble×8, subcmd_id, data...]
// Set Player Lights = subcmd 0x04, data 1 字节 bit0-3 = LED1-4
for (idx, dev) in devices.enumerated() {
    // 读 Product 字符串辨认设备
    var product = "?"
    if let prodRef = IOHIDDeviceGetProperty(dev, "Product" as CFString) as? String {
        product = prodRef
    }
    print("\n--- 设备 #\(idx): \(product) ---")

    for counter in 0..<4 {
        var buf = [UInt8](repeating: 0, count: 49)
        buf[0] = UInt8(counter & 0xFF)   // global packet counter
        buf[9] = 0x04                    // subcmd: Set Player Lights
        buf[10] = 0x0F                   // 全部 4 颗 LED
        let n = buf.withUnsafeBufferPointer { ptr -> IOReturn in
            // IOHIDDeviceSetReport(dev, reportType, reportID, report, reportLength)
            return IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput,
                                        CFIndex(0x01), ptr.baseAddress!, CFIndex(buf.count))
        }
        print("  SetReport counter=\(counter) -> 返回 \(n) (0=成功)")
        usleep(150_000)
    }
}

print("\n>> 现在观察 Joy-Con LED 灯是否变化（3 秒）...")
sleep(3)
print("==== 判据 ====")
print("LED 变化（新灯亮/全亮 4 颗）→ IOKit Set-Report 通路 OK，进阶段 3。")
print("灯无变化 → IOKit Set-Report 对 Joy-Con 也无效，需止损。")
