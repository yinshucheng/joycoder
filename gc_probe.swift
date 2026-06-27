import Foundation
import GameController

/// 验证 macOS GameController 框架能否读到 Joy-Con 的按键/摇杆。
/// 这绕过裸 HID，用系统级手柄驱动。能读到按键 = 方案可行。

print("=== GameController 探测 ===")
print("已连接手柄数: \(GCController.controllers().count)")

func describe(_ c: GCController) {
    print("\n控制器: \(c.vendorName ?? "?")  category=\(c.productCategory)")
    if let gp = c.extendedGamepad {
        print("  类型: extendedGamepad")
        gp.valueChangedHandler = { _, element in
            var hits: [String] = []
            if gp.buttonA.isPressed { hits.append("A") }
            if gp.buttonB.isPressed { hits.append("B") }
            if gp.buttonX.isPressed { hits.append("X") }
            if gp.buttonY.isPressed { hits.append("Y") }
            if gp.leftShoulder.isPressed { hits.append("L") }
            if gp.rightShoulder.isPressed { hits.append("R") }
            if gp.dpad.up.isPressed { hits.append("Up") }
            if gp.dpad.down.isPressed { hits.append("Down") }
            if gp.dpad.left.isPressed { hits.append("Left") }
            if gp.dpad.right.isPressed { hits.append("Right") }
            let lx = gp.leftThumbstick.xAxis.value, ly = gp.leftThumbstick.yAxis.value
            if abs(lx) > 0.3 || abs(ly) > 0.3 {
                hits.append(String(format: "Lstick(%.1f,%.1f)", lx, ly))
            }
            if !hits.isEmpty { print("  输入: \(hits.joined(separator: " "))") }
        }
    } else if let gp = c.microGamepad {
        print("  类型: microGamepad（功能有限）")
        _ = gp
    } else {
        print("  ⚠️ 无 extendedGamepad/microGamepad profile —— GCController 不完全支持此手柄")
    }
}

for c in GCController.controllers() { describe(c) }

// 监听连接事件（手柄可能稍后才被系统识别）
NotificationCenter.default.addObserver(forName: .GCControllerDidConnect, object: nil, queue: .main) { note in
    if let c = note.object as? GCController {
        print(">>> 手柄已连接")
        describe(c)
    }
}

print("\n请按手柄按键 / 推摇杆，监听 15 秒...")
let deadline = Date().addingTimeInterval(15)
while Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.2))
}
print("=== 结束 ===")
