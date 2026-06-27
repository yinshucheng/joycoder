import Foundation
import GameController

/// 验证：GameController 能否读到摇杆/IMU 的实时值（轮询方式）。
/// 之前按键 handler 不触发，但摇杆是不同元素——先确认摇杆能读。

GCController.shouldMonitorBackgroundEvents = true
print("=== 摇杆读取验证 ===")

var ctrl: GCController?
func grab(_ c: GCController) {
    print("控制器: \(c.vendorName ?? "?")  category=\(c.productCategory)")
    ctrl = c
}
for c in GCController.controllers() { grab(c) }
NotificationCenter.default.addObserver(forName: .GCControllerDidConnect, object: nil, queue: .main) { n in
    if let c = n.object as? GCController { print(">>> 连接"); grab(c) }
}

print("请推动摇杆 / 倾斜手柄，轮询 15 秒...")
let deadline = Date().addingTimeInterval(15)
var lastPrint = Date()
while Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.03))
    guard let c = ctrl else { continue }
    let prof = c.physicalInputProfile
    // 摇杆通过 Direction Pad X/Y Axis 暴露
    if let dpad = prof.dpads["Direction Pad"] {
        let x = dpad.xAxis.value, y = dpad.yAxis.value
        if abs(x) > 0.15 || abs(y) > 0.15 {
            // 限流打印（每 0.1s 最多一次）
            if Date().timeIntervalSince(lastPrint) > 0.1 {
                print(String(format: "  摇杆: x=%+.2f y=%+.2f", x, y))
                lastPrint = Date()
            }
        }
    }
    // 也尝试读 motion (IMU)
    if let motion = c.motion {
        let g = motion.gravity
        if abs(g.x) > 0.5 || abs(g.y) > 0.5 {
            if Date().timeIntervalSince(lastPrint) > 0.2 {
                print(String(format: "  倾斜(gravity): x=%+.2f y=%+.2f z=%+.2f", g.x, g.y, g.z))
                lastPrint = Date()
            }
        }
    }
}
print("=== 结束 ===")
