# BE201 Hackintosh 无线驱动

Intel BE201（PCI 8086:7740）在 macOS Sequoia 15.7.8（24G824）上的 Wi-Fi 与蓝牙工作区。

Wi-Fi 的目标是原生 AWDL 和连续互通（隔空投送、通用控制、接力等）。范围只到 ax/80MHz，不包含 be、160MHz、6GHz 和 MLO。

## 目录

| 路径 | 内容 |
|---|---|
| `work/airportbz` | Wi-Fi 驱动 AirportItlwm 源码，从 AirportBZ 分出，保留了上游历史 |
| `work/airportbz/docs/be201` | 每个版本的技术说明 `BE201-*.md`：改了什么、测试结果、判断依据 |
| `work/wifi-kit` | Wi-Fi 驱动的构建、测试、打包、安装和实验工具。所有版本共用这一个目录 |
| `work/BE201-CURRENT.md` | 按时间记录的测试结果和结论 |
| `work/awdl`、`work/ax`、`work/research` | AWDL 和 Intel 固件接口的研究脚本与参考代码 |
| `work/be201` | BE201 蓝牙固件驱动源码 |
| `work/be201-*`、`work/bt-*`、`work/ble-*` 等 | 蓝牙补丁（BlueToolFixup / IntelBTPatcher）的各个实验源码 |
| `work/sd` | SD 读卡器 |

## Wi-Fi 驱动的流程

版本号和写进 config 的驱动备注都在 [`work/wifi-kit/release.json`](work/wifi-kit/release.json) 里。以下命令都在仓库根目录运行。

1. 改源码，并在 `work/airportbz/docs/be201/` 写这一版的说明，文件名为 `BE201-AWDL-VIF-<版本>.md`。
2. 修改 `release.json` 里的 `version` 和 `comment`。
3. 编译。输出固定写到 `work/wifi-build/`：

   ```bash
   bash work/wifi-kit/build.sh
   ```

4. 运行 24 组离线测试，结果写到 `work/wifi-kit/checks.json`：

   ```bash
   python3 work/wifi-kit/run_checks.py
   ```

5. 打包。工具包固定写到 `outputs/BE201-WiFi/`：

   ```bash
   python3 work/wifi-kit/package.py
   ```

   - 版本号变了时，工具包里原来的驱动会移到 `outputs/BE201-WiFi/上一版/`，安装脚本会要求 EFI 里正好是这一版。
   - EFI 备份、部署记录和实验日志都留在原处。
6. 挂载 EFI 后，在 `outputs/BE201-WiFi/` 里运行 `install.py --check` 和 `install.py --install`。用法和回退方法见工具包里的 `使用与回退.md`。

### 安装时的约束

- 只写 macOS 同盘的 EFI 分区。
- 别的会话（例如音频驱动）也会改 `config.plist`，所以安装脚本按安装那一刻的 config 生成新 config。
- config 里只改三项：Wi-Fi 驱动备注、`be201_awdl_*` 启动参数和 TakeoffDelay。
- 写入前会再比对一次 config；中途被改过就停止，不写入。
- 蓝牙驱动、机型和 OpenCore 本体保持不变，安装脚本会逐项核对。

## 不在仓库里的内容

下面这些只保存在本机，由 `.gitignore` 排除：

- **`outputs/`：** 可部署的工具包。里面有 kext、EFI 备份、带本机序列号的配置和运行日志。
- **`work/wifi-build/`：** 编译输出。
- **`work/wifi-kit/checks.json`、`work/wifi-kit/tests/`：** 测试结果。
- **`work/airportbz-deps/`：** MacKernelSDK，以及 OpenCore 1.0.8 的 `ocvalidate`。
- **`work/*-reference`：** 参考用的其他仓库。
- **其他实验目录里的日志、抓包、plist、json 和目标文件：** 这些可能含有设备地址或账号信息。

笔记里的对端 MAC 地址和 IDS 标识已替换成占位符。实验工具生成的 `runtime-*.json`、`roc-*.txt` 和手机日志可能含有设备、网络和账号信息，不要提交或上传。
