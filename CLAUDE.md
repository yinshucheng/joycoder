# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这个项目是什么

把 Switch Joy-Con 映射成 macOS 操作，**面向 AI Coding 场景脱离键盘**：右摇杆控鼠标 + 按键 DIY（语音触发、回车、删除、快捷键）。铁律边界——**语音覆盖文字输入，手柄管控制**（不做手柄拼字母/虚拟键盘）。完整产品定位与 backlog 见 `README.md`，那是产品意图的权威来源。

`joycon.py` 是唯一的成品入口，也是仓库里唯一的代码文件。早期一堆探测/验证脚本（`*.swift` / `probe*.py` / `test_*.py` 等）已在开源清理时删除；它们硬学来的协议结论都沉淀进了本文件下方的「关键事实」。

## 运行与开发

```bash
# 运行成品（首次会自动建 .venv 并装 requirements.txt）
./start.sh
```

`start.sh` 自动：① 用 `brew --prefix hidapi` 定位 hidapi 并设 `DYLD_LIBRARY_PATH`（不写死版本）；② 挑一个 3.10+ 的 python 建 `.venv`；③ 装依赖后运行 `joycon.py`。

- **需要 Python 3.10+**：macOS 自带的 3.9 装不上 pyobjc 12.x。
- **必须设 `DYLD_LIBRARY_PATH` 指向 hidapi**（`start.sh` 已处理），否则 `hid` 包加载不到动态库。
- **必须用 `hid`（ctypes）包，不能用 PyPI `hidapi`（cython）**——后者在较新 macOS 枚举不到 Joy-Con。
- **`joycon-python` 隐式依赖 `PyGLM`**（陀螺仪模块），未在其依赖声明里，已单列进 `requirements.txt`。
- 没有测试框架/lint/构建系统。验证方式 = 连上手柄手动跑 `./start.sh` 看输出（happy-path 风格，符合"每阶段先有 happy path 再往下"的开发约定）；纯逻辑可 `import joycon` 而不抢占手柄连接。

## 跑起来的前置条件（容易踩的坑）

- **辅助功能权限**：系统设置→隐私与安全性→辅助功能，给终端授权，否则 pynput/Quartz 控制鼠标键盘无效。
- **关掉 Steam**：Steam 后台会接管手柄输入，导致按键时灵时不灵——这是早期"按键间歇不上报"的真凶。
- 蓝牙先连上右 Joy-Con；`joycon.py` 会等待并自动重连。

## 架构与关键事实

成品架构很简单（单文件 `joycon.py`），但依赖几条**硬学来的协议事实**，改动前务必理解：

- **持续持有连接是核心**：pyjoycon 初始化时发激活 subcommand 并起后台线程持续读 0x30 报告，按键/摇杆才会上报。早期用裸 hid/IOKit **间歇读**时手柄处于静默态，误判为"读不到按键"。任何重写都必须保持全程持有连接。
- **活性检测靠 timer 字节**：0x30 报告的 `byte[1]` 是每帧 +3 的 timer。pyjoycon 后台读线程崩溃时 `get_status()` 不抛异常但 timer 卡住；`joycon.py` 据此（约 1 秒不变）判定断线并重连。重连时务必先释放旧连接（`jc._close()`）并安全松开任何 hold 中的键（如 Fn）。
- **Fn 键是修饰键不是普通键码**：用 `CGEventCreateKeyboardEvent` + `kCGEventFlagsChanged` + `kCGEventFlagMaskSecondaryFn` 模拟（见 `fn_down`/`fn_up`），用于长按唤起语音听写。普通 keyDown/keyUp 无效。
- **单只 Joy-Con 横握会串键**：相邻按键可能同时上报（按 A 出 a+b）。点击型动作加了 `DEBOUNCE` 防抖。
- 0x30 报告布局：`byte[0]=0x30, [1]=timer, [2]=电池/连接, [3..5]=按键位, [6..11]=摇杆, [12..]=IMU`。激活序列：report 0x01 发 `0x40 arg=0x01`(Enable IMU)、`0x03 arg=0x30`(Set report mode)。

## 左右手柄自动检测 + Profile

`joycon.py` 不再写死右手柄。`connect()` 同时找 `0x2007`(右)/`0x2006`(左)，连上哪只就加载 `PROFILES[side]`。每个 profile 含：摇杆侧（`stick`）、摇杆标定（`cal`，h/v 各一组 `(中心,最小,最大)`，左右实测值不同）、按键映射（`mapping`）。`norm()` 接收 cal 三元组。重连时**重新检测侧别**，允许中途换手柄。

- **左右都连着时优先右手柄**（保持老行为）；右手柄被别的进程独占时自动 fallback 到左手柄。
- **同一只手柄同时刻只能被一个进程持有**：要分别测左/右，让另一只被占用或断开蓝牙即可分流。探测真机数据时只对目标 PID 开连接；`import joycon` 做纯逻辑测试不会抢占连接。

## 模式切换（右手柄）

右手柄 profile 带 `switch_key`(`shared.plus`) + `modes`：Plus 在🖱️鼠标模式 / ⬆️方向模式间切。**设计原则：所有按键含义不随模式变（全写进基础 `mapping`），唯一随模式变的是摇杆**——鼠标模式摇杆控光标，方向模式摇杆推动发 ↑↓←→（`stick_direction()` + `DPAD_THRESHOLD`/`DPAD_REPEAT`）。这是用户的硬要求（键位一致才不会按错），改键位务必保持。`modes` 里每项只有 `name`/`stick`；若 profile 不写 `switch_key`/`modes` 即单模式（左手柄就是）。

右手柄实测可用键：`a/b/x/y/r/zr/sl/sr/plus/home`（**SL/SR 内侧键可用**；r-stick 摇杆按下偶尔能读但不稳，勿用）。

## 修改映射

按键映射与标定集中在 `joycon.py` 顶部"配置区"的 `PROFILES`（左右各一套 `mapping`/`cal`），手感参数 `DEADZONE`/`MAX_SPEED`/`DEBOUNCE` 左右共用。动作类型见该区注释：`click`/`key`(值可为 `Key.xxx` 或字符如 `","`)/`combo`/`shell`(边沿触发) 与 `hold_fn`(长按)。新增长按型动作需同时加入 `HOLD_KINDS` 并在 `do_press`/`do_release` 配对处理。

这是 README backlog "profile 系统" 的进行中部分；下一步是配置外置（TOML/JSON）与横握/双手柄同时用——详见 `README.md` 的 Backlog。**刻意未提前抽象横握/双手柄，等真用到再加。**
