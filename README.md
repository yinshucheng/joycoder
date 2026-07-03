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

**准备**:macOS + 一只 Switch Joy-Con。

### 一键安装(推荐)

打开「终端」(启动台里搜"终端"),粘贴这一行回车,它会自动装好一切:

```bash
curl -fsSL https://raw.githubusercontent.com/yinshucheng/joycoder/main/install.sh | bash
```

装完照着提示走 3 步(连手柄蓝牙、开权限、`cd ~/joycoder && ./start.sh`)即可。

> 没装过 Homebrew 的话,脚本会提示你先装一句;装完再跑上面这行。

### 授予辅助功能权限(必须)

系统设置 → 隐私与安全性 → **辅助功能** → 把运行它的终端(Terminal / iTerm)加进去并打开。否则手柄控制不了鼠标键盘。

### 手动安装(开发者)

```bash
brew install hidapi
git clone https://github.com/yinshucheng/joycoder.git
cd joycoder && ./start.sh   # 首次自动建 venv、装依赖
```

需 Python 3.10+(系统自带的 3.9 装不上依赖;`start.sh` 会自动找/提示装)。

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
