import Foundation
import GameController

/// 用 GCController 的 per-element handler 抓单只 Joy-Con 按键事件。
/// 验证：按键能触发 handler = 方案完全可行，可进下一步做鼠标控制。

print("=== GameController 按键监听 ===")

// 命令行程序默认不接收手柄输入，必须开启后台事件监听
GCController.shouldMonitorBackgroundEvents = true

func attach(_ c: GCController) {
    print("控制器: \(c.vendorName ?? "?")")
    let prof = c.physicalInputProfile

    // 给每个按键装 pressedChangedHandler
    for (name, btn) in prof.buttons {
        btn.pressedChangedHandler = { _, _, pressed in
            print("  [\(pressed ? "▼按下" : "▲松开")] \(name)")
        }
    }
    // 方向键/摇杆（Direction Pad）装 valueChangedHandler
    for (name, dpad) in prof.dpads {
        dpad.valueChangedHandler = { _, x, y in
            if abs(x) > 0.2 || abs(y) > 0.2 {
                print("  [摇杆] \(name) = (\(String(format:"%.2f",x)), \(String(format:"%.2f",y)))")
            }
        }
    }
    print("  已装监听，共 \(prof.buttons.count) 按键 + \(prof.dpads.count) 摇杆/方向键")
}

for c in GCController.controllers() { attach(c) }
NotificationCenter.default.addObserver(forName: .GCControllerDidConnect, object: nil, queue: .main) { note in
    if let c = note.object as? GCController { print(">>> 连接"); attach(c) }
}

print("请按手柄各按键 + 推摇杆，监听 15 秒...")
let deadline = Date().addingTimeInterval(15)
while Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
}
print("=== 结束 ===")
