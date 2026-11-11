#!/bin/zsh
# Apple Watch unlock without ranging: this Wi-Fi driver has no FTM ranging. Runs as you, not as root.
# Undo: python3 install.py --watch-unlock-undo
cd -- "${0:A:h}" || exit 1
/usr/bin/python3 install.py --watch-unlock
echo
read "?按回车关闭窗口"
