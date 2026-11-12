中文 | [English](README.en.md)

# BE201 Hackintosh 无线驱动：Wi-Fi 与蓝牙

Intel BE201（Wi-Fi PCI 8086:7740，蓝牙 USB 8087:0037）在 macOS Sequoia 上的驱动。支持 15.2 及以后的版本，在 15.7.8（24G824）上验证。

- **Wi-Fi：** 目标是原生 AWDL 和连续互通（隔空投送、通用控制、接力等）。范围只到 ax/80MHz，不包含 be、160MHz、6GHz 和 MLO。
- **蓝牙：** 固件加载、BlueToolFixup 和 IntelBTPatcher 的 BE201 补丁，包括 Apple Music 修复和近期地址路由。

**安装：** 见 [驱动安装指南](docs/INSTALL.md)，包括注入顺序、依赖、必须移除的驱动和可选的启动参数。从 Wi-Fi 1.1.88、BlueToolFixup 2.7.12、IntelBTPatcher 2.5.10 起，不需要再手动加启动参数。

## 功能状态

以下都是在本机（macOS 15.7.8 24G824、Wi-Fi 驱动 1.1.87、蓝牙 2.5.3 / 2.7.11 / 2.5.9）上实测的结果。1.1.88 / 2.7.12 / 2.5.10 只是把这些功能的开关改成默认开启，功能本身没有变化。速度受信道和环境影响很大。

### 已经做到

| 功能 | 说明 |
|---|---|
| Wi-Fi 上网 | 2.4 / 5 GHz，802.11ax，最高 80 MHz。支持开放网络和加密网络、在网络之间切换 |
| 个人热点 / 即时热点 | 能加入 iPhone 的热点。偶尔第一次加入会超时，再试一次即可 |
| AWDL | 开机自动启动 awdl0，不需要手动操作 |
| 隔空投送 | 双向都可以。Mac 和手机在同一个 5 GHz 信道时，Mac 发给手机约 27–33 MB/s，手机发给 Mac 约 39 MB/s，连续传 4 GB 不中断 |
| 隔空投送（连着另一信道的路由器） | 可以传，但只有约 3 MB/s，因为要等手机切到 Mac 所在的信道 |
| 通用控制 | 可用 |
| Apple Watch 解锁 | 可用，但需要先运行一次 `install.py --watch-unlock` 跳过距离测量（见下文“暂时做不到”和[安装指南](docs/INSTALL.md#apple-watch-解锁)） |
| 蓝牙 | 固件上传、经典蓝牙和低功耗蓝牙、蓝牙音频 |
| Apple Music 等蓝牙音频 | 已修复（`-btlfxa2dpcheck`） |
| 接力、通用剪贴板 | 已验证可用，但不是每次开机都稳定（见“进行中”） |

### 进行中

| 功能 | 现状 |
|---|---|
| 连着路由器时在另一信道全速隔空投送 | 用固件的临时驻留（ROC）去手机的信道收发。1.1.86 第一次在 149 信道上和手机互通，但出现了固件错误。1.1.88、1.1.89 在链路换到 149 信道时固件报错，原因是驱动把路由器的 80 MHz 带宽套用到了 149 上；1.1.90 改为 20 MHz 后不再报错，149 上能双向收发，手机也能看到电脑，但发给手机的单播帧没有一帧收到确认：1.1.91 查明它们是在驻留窗口之外被固件放弃的；1.1.92 让这些帧在驱动里等到驻留开始再发，等待测试 |
| 连续互通相机、随航 | 低延迟接口 llw0 已经建好，UMI 已应答，RTG 也已激活，但还没有画面。目前暂停 |
| 接力的稳定性 | 有的开机可用，有的不可用，原因还没查清，目前只做观察。关闭“隔空播放接收器”之后，有记录的几次开机都正常 |

### 暂时做不到

| 功能 | 原因 |
|---|---|
| Wi-Fi 7（be）、160 MHz、6 GHz、MLO | 不在本项目范围内 |
| 两个信道同时工作（第二个 PHY） | 这版固件不会从另一个 PHY 上的链路发包，已经验证过，不再继续。改用临时驻留（ROC）的方案 |
| NAN | 这版固件（-92）没有 NAN 能力 |
| Apple Watch 解锁时的距离测量 | 驱动没有 FTM 测距能力，所以只能跳过测距 |
| iPhone 镜像 | 在 sharingd 的认证阶段失败。很可能是因为没有 T2 芯片，和 Wi-Fi 无关，但没有证实 |
| Sequoia 15.0、15.1 及更早的系统 | Wi-Fi 驱动需要 15.2 引入的 IO80211 接口 |
| 24G824 以外的 Sequoia 版本上的 AWDL 和蓝牙补丁 | AWDL 用到了从 24G824 读出来的私有结构，所以默认关闭；可以手动打开，但没有验证过。蓝牙补丁在这些版本上找不到匹配的代码，就不生效，蓝牙本身照常工作 |

## 目录

| 路径 | 内容 |
|---|---|
| `wifi/airportbz` | Wi-Fi 驱动 AirportItlwm 源码，从 AirportBZ 分出，保留了上游历史 |
| `wifi/kit` | Wi-Fi 的构建、测试、打包、安装和实验工具，所有版本共用 |
| `bluetooth/firmware` | BE201BluetoothFirmware：上传蓝牙固件，含 `fw/` 里的 Intel 固件 |
| `bluetooth/bluetoolfixup` | BlueToolFixup：系统蓝牙进程的 BE201 补丁 |
| `bluetooth/intelbtpatcher` | IntelBTPatcher：控制器命令与事件的补丁 |
| `bluetooth/rpa-payload` | 生成 BlueToolFixup 用的 `AuthenticatedRPAPatch.hpp` |
| `bluetooth/release.json` | 三个蓝牙驱动的版本、说明、固定的编译日期和 EFI 里二进制的哈希 |
| `docs/wifi` | Wi-Fi 每个版本的技术说明：改了什么、测试结果、判断依据 |
| `docs/BE201-CURRENT.md` | 按时间记录的测试结果和结论 |
| `research` | AWDL、Intel 固件接口和蓝牙协议栈的研究脚本与参考代码 |

## 依赖

依赖都放在 `deps/`，不提交到仓库，只在本机保留：

| 路径 | 用途 |
|---|---|
| `deps/MacKernelSDK` | Wi-Fi 编译。打包时会核对它的哈希（`wifi/kit/sdk-manifest.sha256`） |
| `deps/MacKernelSDK-3f75008` | 蓝牙编译（acidanthera MacKernelSDK 3f75008） |
| `deps/Lilu` | 蓝牙编译（Lilu 1.7.3 源码，用到 `Library/plugin_start.cpp`） |
| `deps/ocvalidate` | OpenCore 1.0.8 的配置检查工具 |
| `deps/system-symbols-24G824.txt` | 24G824 内核导出符号，用来检查驱动没有引用不存在的符号 |
| `deps/python` | capstone 5.0.9（`rpa-payload` 用） |

编译输出写到 `build/wifi` 和 `build/bluetooth`。参考用的其他仓库放在 `reference/`。

## Wi-Fi 的流程

版本号和写进 config 的驱动备注都在 [`wifi/kit/release.json`](wifi/kit/release.json) 里。以下命令都在仓库根目录运行。

1. 改源码，并在 `docs/wifi/` 写这一版的说明，文件名为 `BE201-AWDL-VIF-<版本>.md`。
2. 修改 `release.json` 里的 `version` 和 `comment`。
3. 编译：

   ```bash
   bash wifi/kit/build.sh
   ```

4. 运行 24 组离线测试：

   ```bash
   python3 wifi/kit/run_checks.py
   ```

5. 打包。工具包固定写到 `outputs/BE201-WiFi/`：

   ```bash
   python3 wifi/kit/package.py
   ```

   版本号变了时，工具包里原来的驱动会移到 `outputs/BE201-WiFi/上一版/`，安装脚本会要求 EFI 里正好是这一版。EFI 备份、部署记录和实验日志都留在原处。
6. 挂载 EFI 后，在 `outputs/BE201-WiFi/` 里运行 `install.py --check` 和 `install.py --install`。用法和回退方法见工具包里的 `使用与回退.md`。

## 蓝牙的编译

```bash
python3 bluetooth/build.py
```

- **输出位置：** 三个驱动分别编到 `build/bluetooth/<目录>/`。
- **与 EFI 比对：** 每个驱动的结果都会和 EFI 里的二进制比对。版本没改时，编出来的结果和 EFI 里的逐字节一致。
- **发新版本：** 在 `release.json` 里同时改 `version`、`note` 和 `source_date_epoch`。
- **固件驱动的版本号：** 写在 `bluetooth/firmware/Info.plist` 里。

## 安装时的约束

完整的安装步骤见 [驱动安装指南](docs/INSTALL.md)。本项目自己的安装脚本还有下面这些约束：

- 只写 macOS 同盘的 EFI 分区。
- 本机的另一个项目（音频驱动）也会改 `config.plist`。安装脚本按安装那一刻的 config 生成新 config，只改三项：驱动备注、本项目的启动参数（已默认开启的那些会被去掉）和 TakeoffDelay。写入前会再比对一次，中途被改过就停止。
- 工具包一次安装 AirportItlwm、BlueToolFixup 和 IntelBTPatcher，每个都保留上一版作为恢复副本。蓝牙固件驱动、机型和 OpenCore 本体保持不变，安装脚本会逐项核对。

## 不在仓库里的内容

下面这些只保存在本机，由 `.gitignore` 排除：

- **`outputs/`：** 可部署的工具包。里面有 kext、EFI 备份、带本机序列号的配置和运行日志。
- **`deps/`、`build/`、`reference/`：** 依赖、编译输出和参考仓库。
- **测试结果：** `wifi/kit/checks.json` 和 `wifi/kit/tests/`。
- **蓝牙和研究目录里的测试记录、抓包、plist、json 和生成的补丁页面：** 这些可能含有设备地址、账号信息或 Apple 的代码。

笔记里的对端 MAC 地址和 IDS 标识已替换成占位符。实验工具生成的 `runtime-*.json`、`roc-*.txt` 和手机日志可能含有设备、网络和账号信息，不要提交或上传。

## 许可

- **Wi-Fi 驱动：** 沿用 AirportBZ / itlwm 的许可，见 `wifi/airportbz/LICENSE`。
- **Wi-Fi 固件：** 见 `wifi/airportbz/LICENCE.bz-firmware`。
- **蓝牙驱动：** 各目录的 `LICENSE`。
- **Intel 蓝牙固件：** 见 `bluetooth/firmware/fw/LICENCE.ibt_firmware`。
