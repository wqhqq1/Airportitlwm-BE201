# 本机 BE201 HE / 802.11ax 开发检查点

基线：AirportBZ `0ccab1627764406861fb9eb0a06ca36e31b4440f`。
已实机确认的 ac 源码：本地提交 `c23ae6d`，版本 1.0.1；ac / 80MHz 已由用户确认。
当前 HE 候选：1.1.0，仅本机 PCI 8086:7740、Sequoia 15.7.8 / 24G824。

本次接入 API92 MAC_CONFIG v2、LINK_CONFIG v2 和固定 STA_CONFIG v1 的 HE 参数。
固件命令表没有旧 STA_HE_CTXT，也没有 STA_CONFIG 版本条目；后者按 Linux v6.12
固定 96 字节结构处理，和本机已通过的 ac 路径一致。不同的已知版本会关闭 HE。
配置内容包括 BSS color、HE RTS 阈值、默认 packet extension、MU EDCA、HTC、
ACK 能力及 PPE；新 PPE 数组采用每 NSS 五个带宽项的 v2 布局。

HE 最高 80MHz，最多两条空间流；不启用 EHT / be、6GHz、MLO、TWT、WPA3-only。
160MHz 的 HE 能力不发布。路由器为 5GHz / 80MHz / WPA2，已由用户确认启用 ax 混合模式。

源码默认 `NetworkController / BE201EnableHE=false`。本机候选包显式设为 true；
`be201_he=0` 启动参数可覆盖为 ac，旧 `itlwm_he` 参数不影响这个本地构建。
不更换 IO80211 / Skywalk，不安装根补丁，不改变蓝牙、Music 和 ISH 修复。

## 可复现构建

MacKernelSDK 基于 `3f750085caa17ec3a7880f11c11bf4f48cd6a164`，只应用已有 MSI-X 头文件补丁。
使用附带 SDK 和 macOS Command Line Tools，运行：

```sh
MAC_KERNEL_SDK=/absolute/path/to/MacKernelSDK bash scripts/build-be201-local.sh
python3 scripts/test-be201-he.py
```

脚本固定并校验 BE201 固件 / PNVM 哈希，再生成固件源码。API92 / PNVM 未升级。
构建仍为原来的 57 个 Sequoia 源文件；AWDL 接口实验没有加入当前构建。
内核入口继续使用 libkmod `_start/_stop`，`_realmain/_antimain` 均为空。

## 验证范围

ASan / UBSan 检查生产 HE 命令构造、独立 wire offset、非 HE 不写入、新 PPE stride、
MU EDCA 更新 / 清除、真实固件版本门控、HE PHY 速率计算、10 万随机 PPE 和
10 万生产 HE IE 解析输入。另保留启动、DMA、固件边界及连续互通诊断回归检查。

离线检查及编译通过不代表 ax 已通过。需要重启后确认：

1. 新模块版本 / UUID 和 `BE201HERequested`、`BE201HECapabilitiesEnabled`。
2. 关联完成且 `BE201HENegotiated=true`；系统显示 802.11ax / 80MHz。
3. 有实际业务流量时，`BE201TxRateIsHE=true`、发送速率格式和 HE RX 描述符计数增长。
4. 持续双向收发、Wi-Fi 开关、睡眠唤醒、蓝牙 / Music 回归。

RX 计数统计通过初步 RX 检查的描述符，可能包含 A-MSDU 子帧，不能当成已交付 IP
包数或吞吐。PHY 速率不等于实际吞吐；MU / TB 缺 RU 数据时不编造 SU 速率。
当前连续互通只确认用户报告的 iPhone→Mac 基本可用，反向及 iPad 不稳定；
没有通过双向 AirDrop 或 Watch 解锁验收。待 ax 验证通过再继续该路线。

## 参考与许可

Intel Linux v6.12 `mvm/mld-sta.c`、`mvm/link.c`、`mvm/mld-mac.c`、
`mvm/mac80211.c` 和 `fw/api/mac-cfg.h`：GPL-2.0 OR BSD-3-Clause，
Copyright Intel Corporation 2022–2024。已有 AirportBZ / itlwm / OpenBSD 许可继续保留。
本地依赖记录保存对应参考源码的 SHA-256 和固定 tag URL。

https://github.com/torvalds/linux/tree/v6.12/drivers/net/wireless/intel/iwlwifi
