#!/bin/bash
# Joy-Con 控制启动脚本。./start.sh 即可运行。
# 首次运行会自动建虚拟环境并装依赖；之后直接启动。
set -e
cd "$(dirname "$0")"

# hid(ctypes) 包需要能加载到 hidapi 动态库。用 brew 的稳定软链接，不写死版本。
HIDAPI_PREFIX="$(brew --prefix hidapi 2>/dev/null || true)"
if [ -z "$HIDAPI_PREFIX" ] || [ ! -d "$HIDAPI_PREFIX/lib" ]; then
  echo "找不到 hidapi。请先安装：brew install hidapi" >&2
  exit 1
fi
export DYLD_LIBRARY_PATH="$HIDAPI_PREFIX/lib"

# 依赖需要 Python 3.10+（macOS 自带的 3.9 装不上 pyobjc 12.x）。挑一个够新的。
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys; print(sys.version_info[:2] >= (3, 10))' 2>/dev/null || echo False)"
    if [ "$ver" = "True" ]; then PY="$cand"; break; fi
  fi
done
if [ -z "$PY" ]; then
  echo "需要 Python 3.10 或更高版本。安装建议：brew install python@3.12" >&2
  exit 1
fi

# 首次运行：建 venv + 装依赖
if [ ! -d ".venv" ]; then
  echo "首次运行，用 $PY 创建虚拟环境并安装依赖..."
  "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

exec .venv/bin/python -u joycon.py
