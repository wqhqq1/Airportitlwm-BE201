# 升级到 Tahoe（macOS 26）前的准备

Sequoia 的最终版本是 AirportItlwm 1.2.25、BlueToolFixup 2.7.14、IntelBTPatcher 2.5.11、BE201BluetoothFirmware 2.5.3。此后不再更新 Sequoia 版本。

这份说明只记录 Sequoia 版本驱动在 Tahoe 上的行为，以及移植时要处理的地方。EFI 和驱动的修改不在这里做。

## 内核范围（已经限制好）

| 驱动 | 驱动自身的限制 | EFI 配置（MinKernel–MaxKernel） |
|---|---|---|
| AirportItlwm 1.2.25 | 只在 Darwin 24.2 及以后的 24.x 上启动（`AirportItlwmV2.cpp`，按 15.2 的 IO80211Family 编译） | 24.2.0–24.99.99 |
| BlueToolFixup 2.7.14 | Lilu 只在 Sequoia 上启动它（原来是 Monterey–Sequoia） | 24.0.0–24.99.99 |
| IntelBTPatcher 2.5.11 | Lilu 只在 Sequoia 上启动它（原来是 MountainLion–Tahoe） | 24.0.0–24.99.99 |
| BE201BluetoothFirmware 2.5.3 | 无。它只负责上传固件，没有 Sequoia 专用代码 | 24.0.0–24.99.99 |

升级到 Tahoe（Darwin 25）后，按现在的 EFI 配置，这四个驱动都不会注入，所以 BE201 的 Wi-Fi 和蓝牙都不可用，直到移植完成。不会因为这些驱动发生内核崩溃。

## 移植时要处理的 Sequoia 专用部分

- **Wi-Fi：**
  - IO80211Family / Skywalk 的私有接口（虚函数表、结构偏移）按 macOS 15.2 编译（`-D__IO80211_TARGET=150200`，`build-sequoia-macos.sh`）；
  - AWDL 布局只在 24G824、24H241 上验证过（`ItlAwdlLayoutVerified`），其他版本 AWDL 默认关闭；
  - 安装工具的 `VERIFIED_BUILDS = ('24G824', '24H241')`，以及它对 macOS 15 的检查。
- **蓝牙：**
  - BlueToolFixup 的 bluetoothd 补丁是按 24G824/24H241 的代码字节写的（`BE201Patches.hpp`），Tahoe 上要重新读取和匹配；
  - IntelBTPatcher 里按 `KernelVersion::Sequoia` 区分的路径。
- **EFI 配置：** 四个驱动的 `MaxKernel` 要改成 Tahoe 的范围，最好给 Sequoia 版和 Tahoe 版分别设置内核范围，便于回退。

## 升级前

- 备份整个 EFI 分区。注意本机 EFI 分区的磁盘编号会变（这次开机是 disk0s3；disk1s3 是 Windows 分区），挂载前先用 `diskutil list` 确认是 `EFI NO NAME`。
- 备份 Sequoia 系统卷（Time Machine 或可启动的克隆），以便回退。
- 桌面上的 4 个 `-Sequoia.zip` 就是最终的 Sequoia 驱动，和 EFI 里的文件一致。
