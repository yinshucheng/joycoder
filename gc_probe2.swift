import Foundation
import GameController

/// 探测单只 Joy-Con 在 GameController 下暴露的所有 input 元素。
/// macOS 支持单只 Joy-Con，但 profile 特殊——遍历 physicalInputProfile 找按键。

print("=== GameController 深度探测 ===")

func probe(_ c: GCController) {
    print("\n控制器: \(c.vendorName ?? "?")  category=\(c.productCategory)")
    // physicalInputProfile 暴露所有元素（按键/摇杆/方向键），不分 profile 类型
    let prof = c.physicalInputProfile
    print("  所有元素 (\(prof.elements.count) 个):")
    for (name, _) in prof.elements {
        print("    element: \(name)")
    }
    print("  buttons keys: \(prof.buttons.keys.sorted())")
    print("  axes keys: \(prof.axes.keys.sorted())")
    print("  dpads keys: \(prof.dpads.keys.sorted())")
}

var theController: GCController?
for c in GCController.controllers() { probe(c); theController = c }
NotificationCenter.default.addObserver(forName: .GCControllerDidConnect, object: nil, queue: .main) { note in
    if let c = note.object as? GCController { print(">>> 连接"); probe(c); theController = c }
}

print("\n请按手柄各按键 + 推摇杆，轮询监听 15 秒...")
let deadline = Date().addingTimeInterval(15)
var prev = ""
while Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
    guard let c = theController else { continue }
    let prof = c.physicalInputProfile
    var active: [String] = []
    for (name, btn) in prof.buttons where btn.isPressed {
        active.append("BTN:\(name)")
    }
    for (name, axis) in prof.axes where abs(axis.value) > 0.3 {
        active.append("AXIS:\(name)=\(String(format:"%.2f",axis.value))")
    }
    for (name, dpad) in prof.dpads {
        if abs(dpad.xAxis.value) > 0.3 || abs(dpad.yAxis.value) > 0.3 {
            active.append("DPAD:\(name)=(\(String(format:"%.1f",dpad.xAxis.value)),\(String(format:"%.1f",dpad.yAxis.value)))")
        }
    }
    let cur = active.sorted().joined(separator: "  ")
    if cur != prev && !cur.isEmpty {
        print("  >>> \(cur)")
    }
    prev = cur
}
print("=== 结束 ===")
