#!/bin/bash
# Joy-Con 控制启动脚本。双击或 ./start.sh 即可运行。
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/hidapi/0.15.0/lib
exec .venv312/bin/python -u joycon.py
