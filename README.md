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

## 给 AI Agent(把这一节连同本 README 丢给你的 coding agent,它能照着装好)

你(agent)的目标:在这台 macOS 上把 joycoder 装好并能运行。按顺序执行,每步用给出的检查判断成败,失败查「常见故障」。

**环境事实(照做,别自作主张换方案)**
- 仅支持 **macOS**(用了 Quartz / pynput 的 mac 原生事件)。
- 需 **Python 3.10+**;macOS 自带的 3.9 装不上 `pyobjc`,会失败。
- 底层 HID 必须用 **`hid`(ctypes)** 包,**不要**用 PyPI 的 `hidapi`(cython)——后者在较新 macOS 枚举不到 Joy-Con。二者都靠 `brew install hidapi` 提供的动态库,运行时需要 `DYLD_LIBRARY_PATH` 指向它(`start.sh` 已自动处理,手动跑才需自己设)。
- `joycon-python` 隐式依赖 `PyGLM`,已在 `requirements.txt` 里显式列出。

**安装步骤**
1. 确认 Homebrew:`command -v brew`。没有 → 让用户装(装 brew 需交互式 sudo,agent 不要代跑):`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. 装 hidapi:`brew install hidapi`。检查:`brew --prefix hidapi` 有输出。
3. 拉代码:`git clone https://github.com/yinshucheng/joycoder.git ~/joycoder && cd ~/joycoder`
4. 一键装 + 起:`./start.sh`(首次自动挑 3.10+ 的 python 建 `.venv`、装依赖、设好 `DYLD_LIBRARY_PATH` 再运行)。
   - 也可直接 `curl -fsSL https://raw.githubusercontent.com/yinshucheng/joycoder/main/install.sh | bash` 一步到位。

**成功判断**:运行后终端打印 `Joy-Con 控制已启动。` 和 `等待手柄连接...`。**这就是装成功了**——即使没接手柄,进程停在等待也算通;接上手柄后会打印 `✓ 手柄已连接`。

**两件 agent 代替不了、必须提醒用户手动做的事**:
- **蓝牙连 Joy-Con**:长按手柄侧边小圆钮进配对,系统设置→蓝牙里连上。
- **辅助功能权限**:系统设置→隐私与安全性→辅助功能→打开运行它的终端。**没开的话:程序正常跑、能读到手柄,但鼠标键盘纹丝不动。** 这是最常见的"装好了却没反应"。

**常见故障 → 对策**
| 现象 | 原因 / 对策 |
|------|-------------|
| `No module named 'glm'` | `requirements.txt` 没装全,重新 `.venv/bin/pip install -r requirements.txt` |
| 装 `pyobjc-framework-Quartz` 报 `Requires-Python >=3.10` | 用了 3.9,换 3.10+(`brew install python@3.12`) |
| `找不到 hidapi` | 没 `brew install hidapi` |
| 能读手柄但鼠标不动 | 没开辅助功能权限(见上) |
| 按键时灵时不灵 | 后台开着 Steam,关掉它或关其控制器支持 |
| 光标乱跳/连发 | 调 `joycon.py` 顶部的 `DEADZONE`/`MAX_SPEED`/`DEBOUNCE` |

**改键位**:全部映射在 `joycon.py` 顶部 `PROFILES` 配置区,动作类型(点击/按键/组合键/shell/长按)见该区注释,改一行即可。

## 工作原理(一句话)

用 [pyjoycon](https://github.com/tocoteron/joycon-python) 全程持有手柄连接、持续读标准报告(0x30),解析摇杆和按键,再用 macOS 原生事件(Quartz / pynput)模拟鼠标键盘。**全程持有连接是关键**——间歇性读取会让手柄进入静默态,按键就上报不了。

## 后续计划

- [ ] 配置外置(TOML/JSON),不改代码就能换键位
- [ ] 完善左手柄 / 横握 / 双手柄的预设
- [ ] 打包成 app,免命令行、自动引导权限
- [ ] 支持多种语音工具与触发方式(长按 / 单击 / 双击)

## License

MIT
