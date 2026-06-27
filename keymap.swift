import Foundation
import IOKit
import IOKit.hid

/// 阶段 3：直接基于 activate_and_read（已验证稳定收 0x30）的结构，
/// 只在 callback 里加按键解析。单设备先跑通。

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

func productID(_ dev: IOHIDDevice) -> UInt32 {
    return (IOHIDDeviceGetProperty(dev, "ProductID" as CFString) as? UInt32) ?? 0
}

// 选第一个设备做解析
let dev0 = devices[0]
let pid0 = productID(dev0)
let side0 = (pid0 == 0x2006) ? "L" : "R"
let keys0: [(Int, Int, String)] = (side0 == "L")
    ? [(3,0,"Down"),(3,1,"Up"),(3,2,"Right"),(3,3,"Left"),(3,4,"SR-L"),(3,5,"SL-L"),(3,6,"L"),(3,7,"ZL"),
       (4,0,"Minus"),(4,1,"StickL"),(4,2,"Capture")]
    : [(3,0,"Y"),(3,1,"X"),(3,2,"B"),(3,3,"A"),(3,4,"SR-R"),(3,5,"SL-R"),(3,6,"R"),(3,7,"ZR"),
       (4,0,"Plus"),(4,1,"StickR"),(4,2,"Home")]
var prevState0: [UInt8] = [0, 0, 0]

var frameCount = 0
let callback: IOHIDReportCallback = { _, _, _, _, reportID, report, reportLength in
    guard reportID == 0x30, reportLength >= 5 else { return }
    frameCount += 1
    let cur: [UInt8] = [report[3], report[4], 0]
    for (byteIdx, bitIdx, name) in keys0 {
        let prevBit = (prevState0[byteIdx - 3] >> bitIdx) & 1
        let curBit = (cur[byteIdx - 3] >> bitIdx) & 1
        if prevBit == 0 && curBit == 1 {
            print("[\(side0)] ▼ 按下  \(name)   (byte\(byteIdx)=0x\(String(format:"%02X", cur[byteIdx-3])))")
        } else if prevBit == 1 && curBit == 0 {
            print("[\(side0)] ▲ 松开  \(name)")
        }
    }
    prevState0 = cur
}

func sendSubcmd(_ dev: IOHIDDevice, counter: UInt8, subcmd: UInt8, data: [UInt8]) {
    var buf: [UInt8] = [counter, 0x00,0x01,0x40,0x40, 0x00,0x01,0x40,0x40, subcmd]
    buf.append(contentsOf: data)
    while buf.count < 49 { buf.append(0) }
    _ = buf.withUnsafeBufferPointer { ptr -> IOReturn in
        IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, CFIndex(0x01), ptr.baseAddress!, CFIndex(buf.count))
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

// 激活（完全复刻 activate_and_read）
print("=== 阶段3 按键解析（设备0: \(side0)）===")
var counter: UInt8 = 0
for dev in devices {
    sendSubcmd(dev, counter: counter, subcmd: 0x40, data: [0x30]); counter &+= 1
    usleep(100_000)
    sendSubcmd(dev, counter: counter, subcmd: 0x03, data: [0x01]); counter &+= 1
    usleep(100_000)
    sendSubcmd(dev, counter: counter, subcmd: 0x48, data: [0x01]); counter &+= 1
    usleep(100_000)
}
print("激活完成，监听中...按手柄按键，Ctrl+C 退出\n")

while true {
    for dev in devices {
        sendSubcmd(dev, counter: counter, subcmd: 0x40, data: [0x30])
        counter &+= 1
    }
    CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 1.0, false)
}
