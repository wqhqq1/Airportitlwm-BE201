# BE201 Hackintosh 无线驱动：Wi-Fi 与蓝牙

Intel BE201（Wi-Fi PCI 8086:7740，蓝牙 USB 8087:0037）在 macOS Sequoia 15.7.8（24G824）上的驱动。

- **Wi-Fi：** 目标是原生 AWDL 和连续互通（隔空投送、通用控制、接力等）。范围只到 ax/80MHz，不包含 be、160MHz、6GHz 和 MLO。
- **蓝牙：** 固件加载、BlueToolFixup 和 IntelBTPatcher 的 BE201 补丁，包括 Apple Music 修复和近期地址路由。

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

- 只写 macOS 同盘的 EFI 分区。
- 别的会话（例如音频驱动）也会改 `config.plist`。Wi-Fi 安装脚本按安装那一刻的 config 生成新 config，只改 Wi-Fi 驱动备注、`be201_awdl_*` 启动参数和 TakeoffDelay 三项。写入前会再比对一次，中途被改过就停止。
- 安装 Wi-Fi 时，蓝牙驱动、机型和 OpenCore 本体保持不变，安装脚本会逐项核对。

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
