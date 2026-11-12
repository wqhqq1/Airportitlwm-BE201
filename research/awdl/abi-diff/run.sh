#!/bin/bash
# Compare IO80211Family (and the families AWDL uses) between the saved 24G824 Boot KC and this machine's.
# Usage: bash research/awdl/abi-diff/run.sh [old-kc-dir]   (default deps/kc-24G824). Read-only; writes to $OUT.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OLD=${1:-deps/kc-24G824}; NEW=/System/Library/KernelCollections/BootKernelExtensions.kc
OUT=${OUT:-build/abi-diff}; mkdir -p "$OUT"; D=research/awdl/abi-diff; PY="python3 -I"
nm -arch x86_64 "$OLD/BootKernelExtensions.kc" > "$OUT/old.nm" 2>/dev/null
nm -arch x86_64 "$NEW" > "$OUT/new.nm" 2>/dev/null
A="deps/python $OLD/BootKernelExtensions.kc $OUT/old.nm $NEW $OUT/new.nm com.apple.iokit.IO80211Family"
$PY $D/kcdiff.py "$OLD/BootKernelExtensions.kc" "$NEW" com.apple.iokit.IO80211Family com.apple.iokit.IOSkywalkFamily com.apple.iokit.IONetworkingFamily com.apple.driver.corecapture | cut -c1-160
$PY $D/fndiff.py $A "$OUT/changed.json"
$PY $D/classify.py $A "$OUT/changed.json" "$OUT/classified.json"
$PY $D/vt.py $A | grep -E "^(DIFF|only|vtables)"
$PY $D/init.py $A | tail -1
echo "Review $OUT/classified.json 'real' entries; AWDL classes there need disp.py/bag.py/one2.py by hand."
