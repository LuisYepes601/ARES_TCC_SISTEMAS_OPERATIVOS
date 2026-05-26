#!/bin/bash
echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║   Ares v3.0 · System Monitor     ║"
echo "  ╚══════════════════════════════════╝"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 not found. Install Python 3.10+ from https://python.org"; exit 1
fi

[ ! -d "venv" ] && python3 -m venv venv

source venv/bin/activate

pip install -q -r requirements.txt

echo "Starting Ares..."
python main.py
