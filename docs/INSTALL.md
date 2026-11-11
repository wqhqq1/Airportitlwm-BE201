中文 | [English](INSTALL.en.md)

# 驱动安装指南

本指南说明如何把 BE201 的 Wi-Fi 和蓝牙驱动装进 OpenCore 的 EFI，包括注入顺序和依赖。返回 [README](../README.md)。

## 适用范围

- **系统：** 只适用于 macOS Sequoia 15.7.8（24G824），x86_64。
  - 蓝牙补丁按 24G824 里系统蓝牙进程的确切代码写成，其他版本不会生效。
  - Wi-Fi 驱动也按 24G824 的内核接口验证过。
- **硬件：**
  - Wi-Fi：Intel BE201，PCI `8086:7740`。
  - 蓝牙：Intel BE201，USB `8087:0037`。
- **引导：** OpenCore 1.0.8。配置用 1.0.8 的 `ocvalidate` 检查。
- **机型：** 本机使用 MacBookPro16,2，之前也在 MacPro7,1 上用过。
- **不需要：** 系统根补丁（OCLP root patch）。驱动用的是系统自带的 IO80211Family 和 IOSkywalkFamily。

## 准备驱动

仓库里不放编好的驱动。按 [README](../README.md) 里的步骤，先编出下面这些文件：

| 驱动 | 版本 | 编译输出 |
|---|---|---|
| `AirportItlwm.kext` | 1.1.87 | `python3 wifi/kit/package.py` 之后在 `outputs/BE201-WiFi/` |
| `BE201BluetoothFirmware.kext` | 2.5.3 | `build/bluetooth/firmware/` |
| `BlueToolFixup.kext` | 2.7.11 | `build/bluetooth/bluetoolfixup/` |
| `IntelBTPatcher.kext` | 2.5.9 | `build/bluetooth/intelbtpatcher/` |

另外需要 [Lilu](https://github.com/acidanthera/Lilu) 1.7.3 或更新的版本（用 RELEASE 版即可）。

Wi-Fi 固件和蓝牙固件都已经编进驱动里，不需要另外放固件文件。

## 必须移除的驱动

下面这些驱动和本项目的驱动重名，或者会抢同一个设备。请把它们从 `Kernel/Add` 里删除或禁用：

| 驱动 | 原因 |
|---|---|
| `IntelBluetoothFirmware.kext`、`IntelBluetoothInjector.kext` | `BE201BluetoothFirmware.kext` 替代它们。它的驱动类也叫 `IntelBluetoothFirmware`，两者同时加载会冲突 |
| 其他版本的 `IntelBTPatcher.kext` | 与本项目的 IntelBTPatcher 同名 |
| BrcmPatchRAM 自带的 `BlueToolFixup.kext` | 同一个 bundle id（`as.acidanthera.BlueToolFixup`），只能保留本项目这一份 |
| `itlwm.kext`、其他版本的 `AirportItlwm.kext` | 同样匹配 `8086:7740`，一张网卡只能有一个 Wi-Fi 驱动 |

EFI 里留着的 `*-recovery.kext` 文件夹没有关系，只要 `Kernel/Add` 里没有启用它们就不会加载。

## 依赖和注入顺序

OpenCore 按 `Kernel/Add` 从上到下的顺序注入驱动，被依赖的驱动必须排在前面。

| 驱动 | 依赖 | 顺序要求 |
|---|---|---|
| `Lilu.kext` | 无 | 放在最前面 |
| `IntelBTPatcher.kext` | Lilu、IOUSBHostFamily | 必须在 Lilu 之后 |
| `BE201BluetoothFirmware.kext` | IOUSBHostFamily（不依赖 Lilu） | 与 IntelBTPatcher 放在一起 |
| `BlueToolFixup.kext` | Lilu | 必须在 Lilu 之后 |
| `AirportItlwm.kext` | IO80211Family、IOSkywalkFamily、IONetworkingFamily、IOPCIFamily、corecapture（都是系统自带，不依赖 Lilu） | 没有硬性要求，放在蓝牙驱动之后即可 |

本机已经验证可用的顺序是：

```text
Lilu.kext                    （第一个）
……其他驱动……
IntelBTPatcher.kext
BE201BluetoothFirmware.kext
BlueToolFixup.kext
AirportItlwm.kext
```

`Kernel/Add` 里这四项的写法如下。注意：`BE201BluetoothFirmware.kext` 里可执行文件的名字是 `IntelBluetoothFirmware`，不是 bundle 名。

| BundlePath | ExecutablePath | MinKernel | MaxKernel |
|---|---|---|---|
| `IntelBTPatcher.kext` | `Contents/MacOS/IntelBTPatcher` | `24.0.0` | `24.99.99` |
| `BE201BluetoothFirmware.kext` | `Contents/MacOS/IntelBluetoothFirmware` | `24.0.0` | `24.99.99` |
| `BlueToolFixup.kext` | `Contents/MacOS/BlueToolFixup` | `24.0.0` | `24.99.99` |
| `AirportItlwm.kext` | `Contents/MacOS/AirportItlwm` | `24.2.0` | `24.99.99` |

这四项的 `Arch` 都填 `x86_64`，`Enabled` 填 `true`，`PlistPath` 都填 `Contents/Info.plist`。

## 启动参数

把下面这些参数加到 `NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/boot-args`，原有的参数保留。

**蓝牙**（本机使用的是下面这一整组）：

| 参数 | 作用 |
|---|---|
| `-btlfxa2dpcheck` | 修正 A2DP 的蓝牙时钟判断。Apple Music 等蓝牙音频需要它 |
| `-be201identity` | 系统信息里把芯片名显示为 Intel BE201，数字标识不变 |
| `-be201leadv` | 让系统改用单一广播的 LE 后端 |
| `-be201addrpause` | 与随机地址更新相关的 LE 补丁，要和 `-be201leadv` 一起用 |
| `-be201lebaseline` | BlueToolFixup 和 IntelBTPatcher 共用的 LE 基础补丁 |
| `-be201nativeaddr` | IntelBTPatcher 按系统原生方式处理控制器地址 |
| `-be201btprobe` | 只读的诊断计数，`-be201rparoute` 需要它 |
| `-be201rparoute` | 用系统验证过的身份解析近期的随机私有地址，并按它路由连接（2.7.11）。要和 `-be201btprobe` 一起用 |

**Wi-Fi：**

| 参数 | 作用 |
|---|---|
| `be201_awdl_vif=1` | 提供 AWDL 接口（awdl0），隔空投送、通用控制等功能需要它 |
| `be201_awdl_auto=1` | 开机后自动启动 AWDL。如果上次启动发生了内核崩溃，会跳过一次 |
| `be201_tlc_diag=1` | 记录速率与加入网络的诊断信息，只读。本项目的安装脚本会检查它 |

不加 `be201_awdl_*` 这两个参数时，Wi-Fi 仍然可以正常上网，只是没有 AWDL。

## 其他配置

- **USB 映射：** 蓝牙接在内部 USB 口上，USB 映射里必须包含这个口。本机用的是 USBToolBox 加 UTBDefault。
- **Kernel/Quirks：** 本机开启了 `DisableIoMapper`。关闭它的情况没有测试过。
- **启动等待：** 本机把 `Misc/Boot/TakeoffDelay` 设为 `100000`，用来在这台机器的 PS/2 键盘上按 Esc 或 0 打开启动菜单。它和驱动本身无关。

## 安装步骤

### 本机：用工具包安装

`outputs/BE201-WiFi/install.py` 只适用于本机。它会核对这台机器的 EFI 分区 UUID、蓝牙驱动的哈希和机型，在别的机器上会直接拒绝运行。

1. 挂载 macOS 同盘的 EFI 分区。
2. 运行检查，它不会改动 EFI：

   ```bash
   python3 outputs/BE201-WiFi/install.py --check
   ```

3. 写入。写入前会先备份整个 EFI：

   ```bash
   python3 outputs/BE201-WiFi/install.py --install
   ```

4. 重启。

回退方法见工具包里的 `使用与回退.md`。

### 其他机器：手动安装

1. 备份整个 EFI 文件夹。
2. 把四个驱动和 Lilu 复制到 `EFI/OC/Kexts/`。
3. 按上面的顺序在 `Kernel/Add` 里添加条目，并移除冲突的驱动。
4. 添加启动参数。
5. 用 OpenCore 1.0.8 的 `ocvalidate` 检查 `config.plist`，确认没有报错。
6. 重启。如果 NVRAM 里已经存过旧的 `boot-args`，请确认 `NVRAM/Delete` 里包含 `boot-args`，或者先重置一次 NVRAM。

## 装好之后怎么确认

```bash
kmutil showloaded --list-only | grep -E 'AirportItlwm|BlueToolFixup|IntelBTPatcher|BE201BluetoothFirmware|Lilu'
```

- 应该看到五个驱动都已加载，版本和上表一致。
- 在“系统信息 → 蓝牙”里，芯片显示为 Intel BE201。
- 加了 AWDL 参数时，`ifconfig awdl0` 能看到这个接口。

如果 Wi-Fi 驱动没有加载，先看 EFI 根目录最新的 `opencore-*.txt`。注意：RELEASE 版 OpenCore 不会写这个日志，需要临时换成 DEBUG 版并把 `Misc/Debug/Target` 设为 `67`。

1.1.54 曾经因为段布局问题被 OpenCore 跳过。现在打包时会用 `oc_layout_check.py` 检查，不会再出现。
