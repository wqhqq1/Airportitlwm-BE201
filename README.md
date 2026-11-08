# BE201 Hackintosh 无线驱动

Intel BE201（PCI 8086:7740）在 macOS Sequoia 15.7.8 上的 Wi-Fi 与蓝牙工作区。Wi-Fi 的目标是原生 AWDL 和连续互通（隔空投送、通用控制、接力等），只做到 ax/80MHz，不包含 be、160MHz、6GHz 和 MLO。

## 目录

| 路径 | 内容 |
|---|---|
| `work/airportbz` | Wi-Fi 驱动 AirportItlwm 源码，从 AirportBZ 分出，保留了上游历史。版本说明见其中的 `BE201-AWDL-*.md` |
| `work/awdl-speed-1154` | 当前版本 1.1.54 的打包、检查和实验工具（`work/awdl-held-1153` 是上一版） |
| `work/BE201-CURRENT.md` | 按时间记录的测试结果和结论 |
| `work/awdl`、`work/ax`、`work/research` | AWDL 和 Intel 固件接口的研究脚本与参考代码 |
| `work/be201` | BE201 蓝牙固件驱动源码 |
| `work/be201-*`、`work/bt-*` | 蓝牙补丁（BlueToolFixup / IntelBTPatcher）的各个实验源码 |
| `work/sd`、`work/ish-stream-0.5.3`、`work/brightness-battery-20261102` | SD 读卡器和亮度相关 |

## 不在仓库里的内容

下面这些只保存在本机，由 `.gitignore` 排除：

- `outputs/`：可部署的工具包。里面有 kext、EFI 备份、带本机序列号的配置和运行日志。
- `work/*-reference`：参考用的其他仓库。
- `work/airportbz-deps`：MacKernelSDK。
- `work/*-build`：编译输出。
- 其他实验目录里的日志、抓包、plist、json 和目标文件。这些可能含有设备地址或账号信息。

提交前已经把笔记里的对端 MAC 地址和 IDS 标识替换成占位符。

## 编译

```bash
MAC_KERNEL_SDK="$PWD/work/airportbz-deps/MacKernelSDK" BUILD_OUTPUT="$PWD/work/be201-awdl-speed54-build" bash work/airportbz/scripts/build-sequoia-macos.sh
```

版本号默认是 1.1.54，可以用 `BE201_BUILD_VERSION` 修改。编译后用 `work/awdl-speed-1154/run_checks.py` 运行离线测试，再用同目录的 `package.py` 生成 `outputs/` 下的工具包。
