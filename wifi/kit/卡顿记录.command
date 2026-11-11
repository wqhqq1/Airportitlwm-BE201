#!/bin/zsh
cd -- "${0:A:h}" || exit 1
/usr/bin/python3 -I stall_history.py
echo
read "?按回车关闭窗口"
