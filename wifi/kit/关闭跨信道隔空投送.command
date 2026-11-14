#!/bin/zsh
cd -- "${0:A:h}" || exit 1
/usr/bin/sudo /usr/bin/python3 -I roc_test.py --off
echo
read "?按回车关闭窗口"
