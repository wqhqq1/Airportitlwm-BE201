#!/bin/bash
# Builds the Wi-Fi driver at the version in release.json into build/wifi (one fixed folder, reused).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VER=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/wifi/kit/release.json")
rm -rf "$ROOT/build/wifi/objects"
MAC_KERNEL_SDK="$ROOT/deps/MacKernelSDK" BUILD_OUTPUT="$ROOT/build/wifi" BE201_BUILD_VERSION="$VER" \
  bash "$ROOT/wifi/airportbz/scripts/build-sequoia-macos.sh"
