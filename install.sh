#!/bin/bash
# joycoder 一键安装。
# 用法（在终端粘贴这一行）：
#   curl -fsSL https://raw.githubusercontent.com/yinshucheng/joycoder/main/install.sh | bash
#
# 做的事：检查 Homebrew → 装 hidapi → 拉代码到 ~/joycoder → 建 venv 装依赖。
# 装完告诉你怎么开权限、连手柄、启动。
set -e

REPO="https://github.com/yinshucheng/joycoder.git"
DEST="$HOME/joycoder"

say()  { printf "\033[1;36m▸ %s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$1"; }

echo ""
say "joycoder 安装开始"

# 1. 系统检查
if [ "$(uname)" != "Darwin" ]; then
  warn "这个工具目前只支持 macOS。"
  exit 1
fi

# 2. Homebrew（装 brew 需要交互式 sudo，管道里跑不了，缺了就明确指引）
if ! command -v brew >/dev/null 2>&1; then
  warn "没检测到 Homebrew。请先装它（macOS 的软件包管理器）："
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  echo "装完 Homebrew 后，重新跑本安装命令即可。"
  exit 1
fi
ok "Homebrew 已就绪"

# 3. hidapi（读手柄的底层库）
if [ -z "$(brew --prefix hidapi 2>/dev/null)" ]; then
  say "安装 hidapi..."
  brew install hidapi
fi
ok "hidapi 已就绪"

# 4. Python 3.10+
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; exit(0 if sys.version_info[:2] >= (3,10) else 1)' 2>/dev/null; then
      PY="$cand"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  say "安装 Python..."
  brew install python@3.12
  PY="python3.12"
fi
ok "Python 已就绪（$PY）"

# 5. 拉代码（已存在则更新）
if [ -d "$DEST/.git" ]; then
  say "更新已有代码（$DEST）..."
  git -C "$DEST" pull --ff-only -q || warn "更新失败，用现有版本继续"
else
  say "下载代码到 $DEST ..."
  git clone -q "$REPO" "$DEST"
fi
ok "代码已就绪"

# 6. 建 venv + 装依赖
say "安装依赖（第一次会花一两分钟）..."
cd "$DEST"
"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
ok "依赖装好了"

# 7. 收尾指引
echo ""
ok "安装完成！接下来 3 步："
echo ""
echo "  1. 蓝牙连上 Joy-Con（长按手柄侧边的小圆钮进入配对，在系统设置→蓝牙里连）"
echo "  2. 开权限：系统设置 → 隐私与安全性 → 辅助功能 → 把「终端」打开"
echo "  3. 启动："
echo "       cd ~/joycoder && ./start.sh"
echo ""
echo "  默认右摇杆控鼠标，ZR 扳机/Y 键长按说话，A=左键 B=回车 X=删除。"
echo "  改键位见 ~/joycoder/README.md"
echo ""
