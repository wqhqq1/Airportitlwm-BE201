中文 | [English](INSTALL.en.md)

# 驱动安装指南

本指南说明如何把 BE201 的 Wi-Fi 和蓝牙驱动装进 OpenCore 的 EFI，包括注入顺序和依赖。返回 [README](../README.md)。

## 适用范围

- **系统：** macOS Sequoia 15.2 及以后的版本，x86_64。
  - Wi-Fi 驱动会拒绝在 Darwin 24.2 以下运行：15.0 和 15.1 的 IO80211 接口不一样。
  - **AWDL（隔空投送、通用控制等）：** 只在 15.7.8（24G824）上默认开启。AWDL 用到了 IO80211Family 的私有结构，这些结构是从 24G824 读出来的。在其他版本上，AWDL 默认关闭，需要手动加 `be201_awdl_vif=1 be201_awdl_auto=1` 才会打开，风险自负。
  - **蓝牙补丁：** 按 24G824 里系统蓝牙进程的确切代码匹配。在其他版本上找不到匹配的代码，就什么也不改。蓝牙本身照常工作。
- **硬件：**
  - Wi-Fi：Intel BE201，PCI `8086:7740`。
  - 蓝牙：Intel BE201，USB `8087:0037`。
- **引导：** OpenCore 1.0.8。配置用 1.0.8 的 `ocvalidate` 检查。
- **机型：** 本机使用 MacBookPro16,2，之前也在 MacPro7,1 上用过。
- **不需要：** 系统根补丁（OCLP root patch）。驱动用的是系统自带的 IO80211Family 和 IOSkywalkFamily。

## 准备驱动

仓库里不放编好的驱动。按 [README](../README.md) 里的步骤编出下面这些文件。运行 `python3 wifi/kit/package.py` 后，前三个都在 `outputs/BE201-WiFi/` 里：

| 驱动 | 版本 | 来源 |
|---|---|---|
| `AirportItlwm.kext` | 1.1.92 | `outputs/BE201-WiFi/` |
| `BlueToolFixup.kext` | 2.7.12 | `outputs/BE201-WiFi/`，或 `build/bluetooth/bluetoolfixup/` |
| `IntelBTPatcher.kext` | 2.5.10 | `outputs/BE201-WiFi/`，或 `build/bluetooth/intelbtpatcher/` |
| `BE201BluetoothFirmware.kext` | 2.5.3 | `build/bluetooth/firmware/` |

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

## 启动参数：默认不需要

从 Wi-Fi 1.1.88、BlueToolFixup 2.7.12、IntelBTPatcher 2.5.10 起，下面这些功能不加启动参数就已经开启：

| 功能 | 以前需要的参数 |
|---|---|
| A2DP 蓝牙时钟修正（Apple Music 等蓝牙音频） | `-btlfxa2dpcheck` |
| 系统信息里显示 Intel BE201 | `-be201identity` |
| 单一广播的 LE 后端 | `-be201leadv` |
| 与随机地址更新相关的 LE 补丁 | `-be201addrpause` |
| BlueToolFixup 和 IntelBTPatcher 共用的 LE 基础补丁 | `-be201lebaseline` |
| IntelBTPatcher 按系统原生方式处理控制器地址 | `-be201nativeaddr` |
| 只读的诊断计数 | `-be201btprobe` |
| 近期随机私有地址的连接路由 | `-be201rparoute` |
| AWDL 接口（awdl0） | `be201_awdl_vif=1` |
| 开机自动启动 AWDL（上次启动发生内核崩溃时会跳过一次） | `be201_awdl_auto=1` |
| 速率与加入网络的只读诊断 | `be201_tlc_diag=1` |

旧参数留在 `boot-args` 里也没有影响。

**想关闭某些功能时用这些参数：**

| 参数 | 作用 |
|---|---|
| `-be201btstock` | 关闭上面所有 BE201 蓝牙补丁。同时再写上某个开关，可以只打开那一个 |
| `be201_awdl_vif=0` | 关闭 AWDL |
| `be201_awdl_auto=0` | 保留 AWDL 接口，但不自动启动 |
| `be201_tlc_diag=0` | 关闭速率诊断 |

**实验开关默认关闭，不会自动打开：**
- ROC 和第二信道：`debug.be201_awdl_roc`、`debug.be201_awdl_phy2`。只在运行 `开始ROC实验.command` 时临时打开，实验结束会自动关回去。
- 低延迟接口 llw0。
- 蓝牙的 `-be201privacyprobe`、`-be201peeraddr`。

## 其他配置

- **USB 映射：** 蓝牙接在内部 USB 口上，USB 映射里必须包含这个口。本机用的是 USBToolBox 加 UTBDefault。
- **Kernel/Quirks：** 本机开启了 `DisableIoMapper`。关闭它的情况没有测试过。
- **启动等待：** 本机把 `Misc/Boot/TakeoffDelay` 设为 `100000`，用来在这台机器的 PS/2 键盘上按 Esc 或 0 打开启动菜单。它和驱动本身无关。

## 安装步骤

### 本机：用工具包安装

`outputs/BE201-WiFi/install.py` 只适用于本机。它会核对这台机器的 EFI 分区 UUID、蓝牙固件驱动的哈希和机型，在别的机器上会直接拒绝运行。它一次安装三个驱动：AirportItlwm、BlueToolFixup 和 IntelBTPatcher。

1. 挂载 macOS 同盘的 EFI 分区。
2. 运行检查，它不会改动 EFI：

   ```bash
   python3 outputs/BE201-WiFi/install.py --check
   ```

3. 写入。写入前会先备份整个 EFI，并从 `boot-args` 里去掉已经不需要的参数：

   ```bash
   python3 outputs/BE201-WiFi/install.py --install
   ```

4. 重启。

回退方法见工具包里的 `使用与回退.md`。

### 其他机器：手动安装

1. 备份整个 EFI 文件夹。
2. 把四个驱动和 Lilu 复制到 `EFI/OC/Kexts/`。
3. 按上面的顺序在 `Kernel/Add` 里添加条目，并移除冲突的驱动。
4. 用 OpenCore 1.0.8 的 `ocvalidate` 检查 `config.plist`，确认没有报错。
5. 重启。

## Apple Watch 解锁

这个 Wi-Fi 驱动没有 FTM 测距能力，而 macOS 解锁时要先测距离，所以需要让系统跳过测距。

用你自己的账户运行下面的命令（不要加 sudo），或者双击工具包里的 `Apple Watch跳过测距.command`：

```bash
python3 outputs/BE201-WiFi/install.py --watch-unlock
```

它实际执行的是：

```bash
defaults write com.apple.sharingd phoneAutoUnlockSkipRanging -bool true
```

```bash
killall sharingd
```

跳过测距以后，只剩蓝牙信号强度这一道检查。手表离得稍远时也可能解锁，安全性比原来低。

要恢复测距，运行：

```bash
python3 outputs/BE201-WiFi/install.py --watch-unlock-undo
```

## 装好之后怎么确认

```bash
kmutil showloaded --list-only | grep -E 'AirportItlwm|BlueToolFixup|IntelBTPatcher|BE201BluetoothFirmware|Lilu'
```

- 应该看到五个驱动都已加载，版本和上表一致。
- 在“系统信息 → 蓝牙”里，芯片显示为 Intel BE201。
- 在 24G824 上，`ifconfig awdl0` 能看到 AWDL 接口。
- `ioreg -l | grep ItlwmAwdlLayoutVerified` 显示 `Yes`，表示当前内核是已验证的版本，所以 AWDL 默认开启。

如果 Wi-Fi 驱动没有加载，先看 EFI 根目录最新的 `opencore-*.txt`。注意：RELEASE 版 OpenCore 不会写这个日志，需要临时换成 DEBUG 版并把 `Misc/Debug/Target` 设为 `67`。

1.1.54 曾经因为段布局问题被 OpenCore 跳过。现在打包时会用 `oc_layout_check.py` 检查，不会再出现。
