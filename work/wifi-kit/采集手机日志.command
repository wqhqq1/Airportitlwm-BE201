#!/bin/zsh
# Reads the USB-connected, trusted iPhone's logs into this folder. Changes nothing on the phone or Mac.
cd -- "${0:A:h}" || exit 1
name="iPhone-$(date +%Y%m%d-%H%M%S)"
sudo /usr/bin/log collect --device --start "$(date -v-90M "+%Y-%m-%d %H:%M:%S")" --output "$name.logarchive" || exit 1
sudo /usr/sbin/chown -R "$USER" "$name.logarchive"
echo "Saved $name.logarchive; it may hold device and account details, so keep it local."
