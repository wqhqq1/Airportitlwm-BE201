#!/bin/bash
# Builds the Wi-Fi driver at the version in release.json into work/wifi-build (one fixed folder, reused).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VER=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/work/wifi-kit/release.json")
rm -rf "$ROOT/work/wifi-build/objects"
MAC_KERNEL_SDK="$ROOT/work/airportbz-deps/MacKernelSDK" BUILD_OUTPUT="$ROOT/work/wifi-build" BE201_BUILD_VERSION="$VER" \
  bash "$ROOT/work/airportbz/scripts/build-sequoia-macos.sh"
