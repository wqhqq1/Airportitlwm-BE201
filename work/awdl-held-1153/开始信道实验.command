#!/bin/zsh
cd -- "${0:A:h}" || exit 1
/usr/bin/sudo /usr/bin/python3 -I channel_test.py
echo
read "?按回车关闭窗口"
