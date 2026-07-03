# joycoder

用 Nintendo Switch Joy-Con 手柄操作你的 Mac —— **专为 AI Coding / 语音写代码场景设计,尽量脱离键盘**。

摇杆控鼠标,手柄按键映射成常用操作(长按说话、回车、删除、快捷键)。核心理念:**语音负责打字,手柄负责控制**。AI 帮你写代码本来就少打字,这个工具把剩下的"控制"也从键盘搬到手里的手柄上。

> 状态:右手柄已调好、日常可用;左手柄有基础配置但未充分打磨。左手柄 / 横握 / 双手柄支持在后续计划里(见文末)。

## 默认按键(右手柄)

| 输入 | 动作 |
|------|------|
| 右摇杆 | 移动鼠标 |
| ZR 扳机 / Y | 长按说话(按住 = 唤起系统语音输入,松开结束) |
| A | 鼠标左键点击 |
| B | 回车 |
| X | 删除(Backspace) |
| SR | Esc(取消 / 中断) |
| Plus | 切换摇杆模式(🖱️ 鼠标 ↔ ⬆️ 方向键) |

映射全部集中在 `joycon.py` 顶部的 `PROFILES` 配置区,改一行就能换键,动作类型见该区注释。

## 快速开始(macOS)

**前置**:macOS + Python 3.10 或更高(系统自带的 3.9 装不上依赖,可 `brew install python@3.12`);一只 Switch Joy-Con,已通过蓝牙连上 Mac(系统设置 → 蓝牙,长按手柄侧边同步键配对)。

```bash
# 1. 安装 hidapi(底层 HID 访问需要)
brew install hidapi

# 2. 克隆并运行(首次会自动建 venv、装依赖)
git clone https://github.com/yinshucheng/joycoder.git
cd joycoder
./start.sh
```

首次运行会自动创建 `.venv` 并安装 `requirements.txt` 里的依赖,之后 `./start.sh` 直接启动。

### 授予辅助功能权限(必须)

系统设置 → 隐私与安全性 → **辅助功能** → 把运行它的终端(Terminal / iTerm)加进去并打开。否则模拟鼠标键盘无效。

## 踩坑提示

- **关掉 Steam**:Steam 后台会接管手柄输入,导致按键时灵时不灵——这是"按键间歇失灵"最常见的真凶。
- **语音输入**:默认长按触发的是 macOS 的语音输入(Fn 修饰键)。用别的语音工具的话,改 `joycon.py` 里 `hold_fn` 的实现即可。
- **单只手柄横握会串键**:相邻按键可能同时上报(按 A 出 a+b),已加防抖(`DEBOUNCE`);还连发就把它调大。
- **手感调节**:摇杆速度 `MAX_SPEED`、死区 `DEADZONE`、防抖 `DEBOUNCE` 都在 `joycon.py` 顶部。

## 工作原理(一句话)

用 [pyjoycon](https://github.com/tocoteron/joycon-python) 全程持有手柄连接、持续读标准报告(0x30),解析摇杆和按键,再用 macOS 原生事件(Quartz / pynput)模拟鼠标键盘。**全程持有连接是关键**——间歇性读取会让手柄进入静默态,按键就上报不了。

## 后续计划

- [ ] 配置外置(TOML/JSON),不改代码就能换键位
- [ ] 完善左手柄 / 横握 / 双手柄的预设
- [ ] 打包成 app,免命令行、自动引导权限
- [ ] 支持多种语音工具与触发方式(长按 / 单击 / 双击)

## License

MIT
