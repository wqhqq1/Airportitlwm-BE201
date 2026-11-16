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

## 进展（2026-11-14 23:04，macOS 26.7.3 25G342）

### 蓝牙（已写入 EFI，等待重启验证）

**调查结果：**
- 升级后四个 Sequoia 驱动都按内核范围被跳过，固件没有上传，系统只看到一个空的占位控制器（BCM_4350C2、地址 NULL）。
- Tahoe 的内核里已经没有 `IOBluetoothHostController` 和 USB 传输类，蓝牙主机栈移到了用户态。IntelBTPatcher 在 Monterey 以后挂接的都是 IOUSBHost 函数，这些在 25G342 的内核集合里还在（管道初始化用的是 26.5 以后的新签名，已有对应挂接）。
- 上游 BrcmPatchRAM 的 "macOS 26 bluetoothd 补丁" 就是 15.4 的芯片检查补丁，我们的 BlueToolFixup 已经有。在 25G342 的 bluetoothd 里，厂商检查、芯片范围检查、15.4 芯片检查三个补丁的原始字节都能找到。
- 所需的 NVRAM 变量（`bluetoothExternalDongleFailed`、`bluetoothInternalControllerInfo`）已经设置。

**新增 Tahoe 版本（Sequoia 版本不变）：**

| EFI 里的驱动 | 版本 | 内核 | 说明 |
|---|---|---|---|
| `IntelBTPatcher-Tahoe.kext` | 2.6.0 | 25.x | IOUSBHost 挂接；BE201 专用开关只在 Sequoia 上生效 |
| `BE201BluetoothFirmware-Tahoe.kext` | 2.5.3 | 25.x | 和 Sequoia 版是同一个文件，只负责上传固件 |
| `BlueToolFixup-Tahoe.kext` | 2.8.0 | 25.x | 只用上游的 bluetoothd 补丁；BE201 专用补丁只在 Sequoia 上生效 |

- 构建：`BE201_TARGET=tahoe python3 bluetooth/<folder>/build.py`，输出在 `build/bluetooth-tahoe`。
- 写入 EFI：`python3 bluetooth/install_tahoe.py --check | --install`。它只写 OpenCore 启动时用的那个 EFI，写之前会先备份整个 EFI。
- 这次的备份在 `EFI-backups/EFI-before-tahoe-bt-20261114-230427`。配置和备份相比，只多了这三项。

**注意：** 在 Tahoe 上用新的编译器重新编译 Sequoia 版驱动，结果和已发布的文件不再逐字节相同。已发布的 Sequoia 驱动（EFI 里的和桌面上的）没有受影响。

### Wi-Fi（只做了盘点，没有修改）

- 现在 Tahoe 上用的是 `AirportItlwm-BZ-Tahoe-backup.kext`（AirportBZ 1.0.0，版本标记 be201-pure-bz-20261023），没有 AWDL（没有 awdl0），所以隔空投送、随航等功能都不可用。
- 我们的源码里已经有 `include/Airport/macOS26` 头文件，但还没有 Tahoe 的编译脚本（现在只有 `-D__IO80211_TARGET=150200` 的 Sequoia 版本）。
- 移植 1.2.25 需要：
  - Tahoe 的编译目标；
  - 按 25G342 重新核对 IO80211Family 和 Skywalk 的虚函数表和结构布局（`ItlAwdlLayoutVerified`）；
  - 让安装工具支持 Tahoe（`VERIFIED_BUILDS` 和对 macOS 15 的检查）。

## BE201 蓝牙补丁移植到 Tahoe（2026-11-14 23:31，已写入 EFI，等待重启验证）

重启后，Tahoe 版蓝牙已经正常工作（Magic Keyboard 已连接），但原先在 Sequoia 上做的 BE201 补丁都没有生效。这次全部移植过来：

| 补丁 | 25G342 上的情况 |
|---|---|
| A2DP 时钟、芯片名、LE 基线、地址暂停、对端地址（选用） | 原来的带掩码模式在 25G342 上各只匹配一处；所在函数和 24H241 的指令相似度 0.98–1.0，补丁位置在函数内的偏移相同 |
| 单广播（LegacyAdv） | 同一个函数，只是两个结构体字段的偏移变了（0x6950→0x69d8、0x88→0x90）；新增 Tahoe 版模式，把这两个偏移也掩掉 |
| 最近 RPA 路由 | `rpa-payload/port.py` 移植到 25G342：两处锚点代码被编译器改写，所以改用手工核对过的锚点（`builds/25G342/anchors.json`）；OI_Time_Now 和分配器的距离也变了。`__TEXT` 末尾只剩 1104 字节，所以 Tahoe 用不带日志的"安静"模块（1058 字节），路由逻辑不变 |
| IntelBTPatcher 的探测、本机地址、LE 基线 | 都在 USB HCI 传输层工作，和系统版本无关，改为在构建对应的内核上启用 |

**测试：**
- `native_route_25g342_test.cpp`：把 25G342 真实的扫描、解析器、AES、过滤代码和路由模块放进私有内存一起运行。它覆盖两个多键调用点、过期、回退、锁竞争、未匹配的 RPA，以及模块缺失或损坏时回退到原生行为。测试通过；24H241 的同一测试也仍然通过。
- `patch_test.cpp`：在 24H241 和 25G342 上都是六个补丁各只打一次，只改了预期的 29 个字节。
- IntelBTPatcher 的 8 个单元测试都通过。passthrough 测试在关掉 sanitizer 时通过；开着 sanitizer 时，这次开机下的 sanitizer 运行时报 SIGILL。被测代码和已提交的版本完全一致。

**版本：** BlueToolFixup-Tahoe 2.9.0、IntelBTPatcher-Tahoe 2.7.0、BE201BluetoothFirmware 2.5.3。备份在 `EFI-backups/EFI-before-tahoe-bt-20261114-233125`。

**注意：** 读取正在运行的 `/usr/sbin/bluetoothd` 时，可能拿到已经被 BlueToolFixup 在内存里改过的页面。移植时用的干净副本在 `outputs/tahoe-bt/bluetoothd.25G342.clean`（以及 `.fat`），其中 5 处通用补丁已恢复成原始字节。

**怎么看是否生效：**
`ioreg -l | grep -E 'BE201(Clock|Name|Legacy|LEBaseline|AddressPause)PatchHits|BE201RPA(Matching|Patched|Rejected)Mask'`
- 各项 PatchHits 大于 0，说明对应补丁已经打上。
- RPA 的 PatchedMask 为 7，说明三页都打上了；RejectedMask 应为 0。

### 验证（2026-11-14 23:41 开机）

- 加载的是 BlueToolFixup 2.9.0、IntelBTPatcher 2.7.0、BE201BluetoothFirmware 2.5.3。
- 补丁命中：
  - A2DP 时钟、芯片名、单广播、LE 基线、地址暂停各 1 次；
  - 对端地址 0 次（这个补丁默认关闭，和 RPA 路由二选一）。
- RPA 路由：三页都匹配、都通过签名校验、都打上了（MatchingMask、ValidatedMask、PatchedMask 都是 7），拒绝 0 次。
- IntelBTPatcher 的探测、本机地址、LE 基线已启用。
- 系统信息里芯片显示为 "Intel BE201"，传输方式是 USB。Magic Keyboard 和 AirPods Pro 都已连接。
- bluetoothd 从开机起一直在运行，没有重启，也没有崩溃报告。
- 待确认：AirPods 连接后的 23:45–23:46，日志里出现了约 490 条 Handsfree（通话音频）断言。上一次开机时没有连 AirPods，所以没法直接对比。需要实际听一下音乐和通话麦克风；如果通话有问题，可以用 `-be201btstock` 对比一次。

## Wi-Fi 移植：离线准备（2026-11-14 23:5x，还没有写入 EFI）

**新增编译脚本** `wifi/airportbz/scripts/build-tahoe-macos.sh`：
- 编译和 Sequoia 版相同的 58 个源文件，改用 macOS26 头文件（`__IO80211_TARGET=260000`），版本号 1.3.0，输出到 `build/wifi-tahoe`。
- Xcode 工程里本来就有一个 Tahoe 目标，但它没有包含 AWDL 接口文件。
- 运行方法：`MAC_KERNEL_SDK=$PWD/deps/MacKernelSDK BUILD_OUTPUT=$PWD/build/wifi-tahoe bash wifi/airportbz/scripts/build-tahoe-macos.sh`
- 日志在 `outputs/tahoe-wifi/build-1.3.0.log`。

**第一次编译：58 个文件里 56 个通过，剩下的错误都和 AWDL 有关：**
- AWDL 用到的 `IO80211VirtualInterface`、`IO80211AWDLProtocol` 目前只有按 Sequoia 24G824 写的布局，大小检查没有通过（288 字节）。
- Tahoe 的 `IO80211Controller` 里没有 `getAwdlInterface`、`setAwdlInterface`、`loadCardCapabilities`；`IO80211SkywalkInterface` 里没有 `setLinkState`；低延迟接口的几个方法也没有了。
- `getSelfMacAddr` 的返回值从结构体改成了指针。
- AirportItlwmV2.cpp 里的 3 个错误，也都出在 AWDL 相关的代码里。

**接下来分两步：**
1. **1.3.0：只做基础 Wi-Fi，AWDL 先不编译进去。** 改动小，重启 1 次验证上网和热点直接接入（Sequoia 版对热点连接做过修复）。
2. **1.3.x：AWDL 移植到 Tahoe。** 先离线核对 25G342 IO80211Family 的类大小、虚函数表和 AWDL 接口的新 API，再重启 2–4 次，验证 awdl0 能否出现、隔空投送、Watch 解锁。Watch 解锁现在失败，日志里报的是 "AWDL info retrieval failed"。

## Wi-Fi 1.3.0（基础 Wi-Fi，不含 AWDL；2026-11-14 23:57 已写入 EFI，等待重启验证）

**代码改动：**
- `AirportItlwmV2.hpp` 新增 `BE201_AWDL_IFACE` 宏，只在 Sequoia 版里为真。在 Tahoe 版里：
  - AWDL 接口类不编译；
  - 五个回调变成空函数；
  - 创建、接管、停止 AWDL 接口的几个函数直接返回"不支持"。
- 驱动自己的 AWDL 射频代码保留。AWDL 在 25G342 上本来就默认关闭，因为它的布局只在 24G824 和 24H241 上验证过。
- Tahoe 版不在 Darwin 25 以外的内核上启动。

**编译和检查：**
- `build-tahoe-macos.sh` 编译 57 个源文件，没有错误，没有警告。
- 965 个导入符号都能在 25G342 的启动内核集合里找到。
- OpenCore 布局检查通过。
- 打包时用 1.2.25 的 Info.plist（依赖库和匹配项和 AirportBZ Tahoe 版一样），只把版本号改成 1.3.0；SHA 32de5477。

**写入 EFI（`wifi/kit/install_tahoe_wifi.py --install`）：**
- 新增 `AirportItlwm-Tahoe.kext`，只在 25.x 内核上加载，排在 AirportBZ 之后；关闭了原来的 `AirportItlwm-BZ-Tahoe-backup.kext`（两者的 bundle ID 相同，只能加载一个）。
- 配置只改了这两处，ocvalidate 没有报错。
- 备份在 `EFI-backups/EFI-before-tahoe-wifi-20261114-235717`。

**回退：** 先挂载 EFI，再运行 `python3 wifi/kit/install_tahoe_wifi.py --fallback`，然后重启。

**注意：** Sequoia 版的源码只多了一个宏，用宏包起来的代码在 Sequoia 版里照常编译；这次没有在 Tahoe 上重新编译 Sequoia 版来核对。

### 1.3.0 验证（2026-11-15 06:00 开机）

- AirportItlwm 1.3.0 已加载，`ItlwmStartupResult = ready`。Wi-Fi 是 en1，已经连上路由器，默认路由走 en1。en0 是另一块有线网卡，不是 Wi-Fi。
- **热点仍然无法直接接入。** 日志里的经过：
  1. 06:24:44 和 06:24:59，sharingd 两次请求 iPhone 打开热点，两次都成功收到网络信息（149 信道，有密码）。
  2. 接着 airportd 按热点的名称发起扫描，准备加入。每次都在几微秒内失败：`Apple80211Scan Failed, err[-3903]`，然后 `Failed to scan for hotspot network`，一直重试。
  3. 驱动没有收到这些扫描请求，内核日志里也没有对应的失败记录。
- **原因：** 反汇编 25G342 的 `IO80211.framework` 中的 `Apple80211Scan`：
  - 扫描指定了网络名称时，如果驱动没有报告能力字节 9 的第 1 位，系统就改用"多网络扫描"请求。
  - 发出多网络扫描之前，它还要检查能力字节 2 的第 6 位。没有这一位，就直接返回 -3903（不支持），根本不发给驱动。
  - 驱动的 WCL 能力表里这两位都没有，所以所有按名称的扫描都被挡住了。`Apple80211ScanDynamic` 里也有同样的检查。WiFiAgent 指定信道的扫描也因此失败。
  - 只指定信道、不指定名称的广播扫描不受影响，所以普通 Wi-Fi 一直能用。
- 能力表的位置：系统框架在绑定接口时，用 `CARD_CAPABILITIES` 读取 21 个字节，存到句柄偏移 0x58 处；`Apple80211Scan` 检查的就是 0x5a 和 0x61，也就是第 2 和第 9 个字节。

## Wi-Fi 1.3.1（热点按名称扫描；2026-11-15 06:42 已写入 EFI，等待重启验证）

**代码改动（只在 Tahoe 版里，`AirportItlwmV2.cpp` 的 `getCARD_CAPABILITIES`）：**
- 能力字节 9 加上第 1 位：按名称的扫描改走普通的单次扫描请求。广播扫描已经在用这条路，它经过 WCL 到达驱动，可以带一个网络名称。
- 能力字节 2 加上第 6 位：与原来那张网卡能力表一致（旧表里字节 2 是 0xFF，字节 9 是 0x02）。系统框架里只有上面那个检查会读它。
- 在这个框架里，字节 9 的其他读取者只看第 4 位（SAE 认证），字节 2 的其他读取者只看第 2、3 位（链路速度）。这次加的两位不影响它们。
- Sequoia 版不变。

**编译和检查：**
- 57 个源文件，没有错误，没有警告。
- 965 个导入符号，和 1.3.0 完全相同。
- 二进制里，字节 2 从 0x0e 变成 0x4e，字节 9 多了 `orb $0x2`，其他不变。
- OpenCore 布局检查通过。Info.plist 和 1.3.0 相比只改了版本号。SHA 223a5eac。
- 1.3.0 的二进制和 kext 保留在 `build/wifi-tahoe/AirportItlwm-1.3.0*`。

**没法提前验证：** 用普通程序按名称扫描，airportd 直接返回缓存结果，不会走到这个检查，所以只能在重启后用热点实测。

**重启后检查：**
- 日志里不再出现 `Apple80211Scan Failed, err[-3903]`。
- 点 iPhone 热点后能看到 `PERSONAL HOTSPOT enabled ... attempting to join now`，后面不再是 `Failed to scan for hotspot network`，而是加入成功。
- 驱动的 `ItlwmWclScanReq` 计数会增加，因为这些按名称的扫描现在会发到驱动。

**写入 EFI（2026-11-15 06:42，disk1s3）：** `install_tahoe_wifi.py --install` 把 `AirportItlwm-Tahoe.kext` 换成 1.3.1（SHA 223a5eac）。配置只改了这一项的注释，ocvalidate 没有报错。备份在 `EFI-backups/EFI-before-tahoe-wifi-20261115-064206`。回退方法和 1.3.0 一样：先挂载 EFI，再运行 `--fallback`。

### 1.3.1 验证（2026-11-15 06:45 开机）

- 1.3.1 已加载，状态正常，en1 正常上网。
- **-3903 消失了**：开机 6 分钟内，成功的 `Apple80211Scan` 有 43 次，只有 6 次失败（发生在开机初期）。到达驱动的扫描请求从 1.3.0 时 28 分钟 6 次，增加到 4 分钟 29 次。
- **热点仍然连不上，但卡的位置往后挪了一步。** 06:47:16 和 06:47:35，iPhone 两次打开热点（149 信道）。airportd 按名称扫描 149 信道 9 次，然后扫描全部信道，每次都报 `Failed to match hotspot network`。18 秒后超时，返回 -3905。
- 每次 149 信道的扫描都是真正的主动扫描，大约 34 ms，每次都能扫到同一信道上的 DLUT-LingShui，但始终没有 iPhone，也没有隐藏网络。
- **原因：** 即时热点是隐藏网络。在 Sequoia 上，iPhone 日志里是 `MIS Mode: Hidden`（1.1.9 的记录），只有探测请求里带上它的名称，iPhone 才会回应。
  - 反汇编 25G342 IO80211Family 的 `IO80211ScanRequest::getScanRequestForDriver`：Tahoe 交给驱动的扫描请求里，除了原来的单个 SSID（0x1c/0x20），还有一个 SSID 列表：数量在 0x1318，条目从 0x131c 开始，每条 0x38 字节，依次是版本 1、长度、SSID，最多 10 条。
  - IO80211.framework 的 `__getScanData` 也是这样填写列表的；没用到的条目保留 0xaa 填充。
  - 驱动只读单个 SSID 字段，那里为空，所以发出去的是不带名称的广播探测。最后一次扫描的 `ItlwmScanSsidLen` 是 0。

## Wi-Fi 1.3.2（扫描请求的 SSID 列表；2026-11-15 06:58 已写入 EFI，07:02 验证热点可以直接接入）

**代码改动：**
- `WCL.hpp` 的 `decodeScan`（只在 Tahoe 版里）：单个 SSID 字段为空时，使用列表里第一个有效条目（版本为 1，长度 1–32）作为探测名称。数量最多按 10 条读，不会读出请求缓冲区之外。
  - 单个 SSID 字段有值时，行为和以前一样。
  - 固件扫描命令本来就会把这个名称放进探测请求，连接状态下的后台扫描也一样。
- `WCL.cpp` 新增诊断属性：
  - `ItlwmWclScanNamed`：带名称的扫描次数；
  - `ItlwmWclScanListNamed`：名称来自列表的次数；
  - `ItlwmWclScanSsidSource`：最近一次名称的来源（0 没有，1 单个字段，2 列表）；
  - `ItlwmWclScanListCount`；
  - `ItlwmWclScanNamedLen`。
- Sequoia 版不变。

**检查：**
- 新测试 `scripts/test-wcl-scan-ssid-list.py` 通过，用 UBSan 加保护页。这台机器上的 ASan 运行库连空程序都会以 SIGILL 退出，所以脚本会自动改用只有 UBSan 的方式。测试覆盖：
  - 单个字段优先；
  - 列表数量 1–12、长度 1–32；
  - 跳过无效条目和 0xaa 填充；
  - 数量为 0 或 0xffffffff；
  - 短缓冲区。
- 编译 57 个源文件，没有错误，没有警告。965 个导入符号和 1.3.1 完全相同。布局检查通过。Info.plist 只改了版本号。SHA 7c08e411。

**写入 EFI：** 这次开机 EFI 是 disk0s3（已经挂载），配置只改了驱动条目的说明文字，ocvalidate 没有报错。备份在 `EFI-backups/EFI-before-tahoe-wifi-20261115-065836`。1.3.1 保留在 `build/wifi-tahoe/AirportItlwm-1.3.1*`。

**重启后检查：**
- 点热点之后，`ItlwmWclScanListNamed` 应该大于 0，`ItlwmWclScanSsidSource` 应该是 2，`ItlwmWclScanNamedLen` 应该等于热点名称的字节数。
- 日志里应该出现 `Detected as a hidden network` 或者加入成功，不再是 `Failed to match hotspot network`。
- 如果 `ItlwmWclScanNamed` 是 0：这些扫描本来就没带名称，问题在系统一侧。
- 如果名称已经带上了，iPhone 却还是不出现：再看固件的探测参数，例如活动驻留时间和是否允许主动探测。

### 1.3.2 验证（2026-11-15 07:00 开机）

- 07:02:22 点热点：`Successful connection to tether device ... took 2.6433 seconds`，随后 `Detected ... as a hidden network`。用户确认可以用了。
- 驱动诊断：带名称的扫描 16 次，全部来自 SSID 列表（`ItlwmWclScanListNamed` 16，`ItlwmWclScanSsidSource` 2），名称长度 19 字节（`ItlwmWclScanNamedLen`），和热点名称一致。
- 剩下的是 AWDL（隔空投送、Watch 解锁），见下一节。

## Wi-Fi 1.4.0（AWDL 移植到 Tahoe；2026-11-15 07:34 已写入 EFI，等待重启验证）

目标：隔空投送、Watch 解锁（需要 awdl0）。1.3.2 的热点修复全部保留。

**离线核对 25G342（工具和结果在 `outputs/tahoe-wifi/`，只读系统文件）：**
- **虚函数表：** 从启动内核集合里解出 `IO80211AWDLProtocol`（568 项，Sequoia 563 项）和 `IO80211VirtualInterface`（505 项，Sequoia 500 项）的虚函数表，每一项都还原成符号名。
  - VirtualInterface 自己覆盖的 53 个方法和 Sequoia 完全一样。
  - 新增 4 项：`flushFlowQueues`、第二个 `p2pMulticastTx`、`signalMulticastPackets`、纯虚的 `setMacAddress`（第 488 项）。
  - `setMacAddress` 是从 SkywalkInterface 挪过来的：`IO80211MacAddressAgent::setMacAddress` 用 `ether_addr&` 调用这一项。
- **63 个 AWDL 处理函数：** 顺序和 Sequoia 一样，整体后移 5 项。其中 51 个由内核 `apple80211get/set*` 分发函数读的槽位直接确认，没有一个不符；其余 12 个没有分发函数指向它们。
- **对象大小：** VirtualInterface 0x130，AWDLProtocol 0x130，SkywalkInterface 0x128（MetaClass 构造函数里读出）。
- **控制器方法：** `getAwdlInterface`、`setAwdlInterface`、`loadCardCapabilities` 在 Tahoe 上仍然存在，是非虚函数，只是 Tahoe 头文件里没有声明。
- **`getSelfMacAddr`：** 按值返回（原生代码把 +0x20/+0x24 拼进 RAX）。Tahoe 头文件写成了指针，已改正。如果按指针用，会把 MAC 地址当成指针去读。
- **请求和事件布局：** 和保存下来的 24G824 内核集合逐个函数对比（`fncmp.py`）。
  - 原生 AppleBCMWLAN 的这些函数：`createProxInterface`、Proximity `start`、`setAWDL_SYNC_FRAME_TEMPLATE`、`setAWDL_PEER_TRAFFIC_REGISTRATION`、`setAWDL_OOB_REQUEST`、`setCOMPANION_SKYWALK_IF_CREATE`，以及 LowLatency 的 `start`/`initBSDInterfaceParameters`。它们的指令数相同，所有小偏移都没变；只有类自己的成员整体后移 0x10，另外日志行号不同。
  - 事件 41（AW start）、51（peer cache）、69（UMI 状态）在两边都由同一个原生函数发出。
  - `IO80211Peer::fillInCacheParams` 写进请求的偏移不变。
  - `IO80211BufferPool::getBuffer` 仍是第 35 项。
  - 用到的 Skywalk 导出函数都还在；`IOSkywalkCloneableNetworkPacket` 的覆盖在 24G824 上也有，不是新情况。

**代码改动：**
- 新头文件 `include/Airport/macOS26/IO80211VirtualInterface.h` 和 `IO80211AWDLProtocol.h`。
- `macOS26/IO80211SkywalkInterface.h`：改正 `getSelfMacAddr`，补上 4 个非虚声明。
- `macOS26/IO80211ControllerV2.h`：补上 3 个非虚声明。
- `BE201_AWDL_IFACE` 在 Tahoe 上也打开；Sequoia 才有的 4 参数 `setLinkState` 只在 Sequoia 版里编译。
- `build-tahoe-macos.sh`：编译 58 个源文件，包括 AWDL 接口。
- `ItlAwdlLayoutVerified`：只在 Tahoe 版里加入 25G342 内核（`xnu-12377.161.15.701.48~2`），注释里写明核对依据。所以 AWDL 在这台机器上默认打开，和 Sequoia 的 1.2.25 一样（ROC 等设置照旧）。

**检查：**
- 新测试 `scripts/test-awdl-vif-abi-tahoe.py` 通过：
  - AWDL 接口 568 项、llw 接口 505 项，逐项和 25G342 原生虚函数表一致；
  - 603 个导入符号都在 25G342 启动内核集合里。
- 原来的 Sequoia ABI 测试 `test-awdl-vif-abi.py` 仍然通过（563 项）。
- `test-awdl-vif.py`（1472 个生命周期场景）和 `test-default-switches.py` 通过。这台机器的 ASan 运行库坏了，所以只用 UBSan。
  - `test-awdl-vif.py` 本身要改两处：它按文本截取源码，要能处理新加的 `#if`；还要定义 `BE201_AWDL_IFACE`。在 HEAD 源码上同样是 1472 个场景通过。
- 编译没有错误；整个驱动的 1124 个导入符号都在启动内核集合里；布局检查通过；SHA e5970690。

**写入 EFI（disk1s3）：**
- `AirportItlwm-Tahoe.kext` 1.4.0 打开。
- 1.3.2 保留为 `AirportItlwm-Tahoe-prev.kext`，条目关闭。
- AirportBZ 备用版仍然关闭。
- ocvalidate 没有报错。
- 备份在 `EFI-backups/EFI-before-tahoe-wifi-20261115-073359`。

**如果 1.4.0 让系统崩溃（进不了系统）：**
1. 在 OpenCore 选单按空格，进入 macOS 恢复，打开终端。
2. 运行 `diskutil list`，找到 `EFI NO NAME`。
3. 运行 `diskutil mount diskXs3`。
4. 运行 `sh "/Volumes/NO NAME/BE201-wifi-previous.sh"`，然后重启，就回到 1.3.2。

这个脚本只改两个 `Enabled`，改之前会把配置复制一份为 `config.plist.before-previous`；PlistBuddy 和 plutil 两条路径都在配置副本上试过。能进系统时，用 `python3 wifi/kit/install_tahoe_wifi.py --previous` 也可以。

**重启后要看：**
- `ifconfig awdl0` 是否出现。
- `ItlwmAwdlLayoutVerified` 是否为 true。
- `ItlwmAwdlVifStep`/`Stage` 是否到 ready。
- 隔空投送能否发现和发送（iPhone、iPad）。
- Watch 解锁。
- 通用控制、随航能否看到设备。

### 1.4.0 结果：进不去系统（2026-11-15 07:37–07:49）

- 07:37 正常注销后，用 1.4.0 重启进不去系统。07:47 配置被改回 1.3.2（`-prev` 条目打开，`-Tahoe` 关闭，内容和回退脚本的结果完全一样）。07:49 开机，进入了系统。
- 用 1.4.0 的那几次启动**一条日志都没有留下**。DumpPanic 在 07:49 处理了 0 个文件，也没有 `.panic` 报告。这台机器以前在同样的 `debug=0x100` 下保存过 panic 报告，所以更像是卡死后被强制关机，而不是 panic。
- 1.4.0 和 1.3.2 在开机时只差一处：25G342 进了已验证列表，所以 `be201_awdl_auto` 会在驱动启动时自动打开 AWDL 的全部开关。这包括通告能力位 32，wifip2pd 随后在开机过程中请求创建 awdl0；还包括跨信道默认设置（phy2、ROC、暂停）。具体卡在哪一步，没有数据，只能下次测试时记录。
- 07:49 那次开机 1.3.2（`-prev` 条目）没有加载，网卡上没有任何驱动属性。用户要求不追究这一点，所以没有调查。下面的 1.4.1 重新放回原来能加载的位置和文件夹名。

## Wi-Fi 1.4.1（AWDL 已编译但开机不启动；2026-11-15 08:00 已写入 EFI，等待重启验证）

**改动（只在 Tahoe 版里）：**
- 不再在开机时自动启动 AWDL，需要启动参数 `be201_awdl_auto=1` 才会启动。
- 跨信道默认设置也不再开机打开，需要 `be201_awdl_xchan=1`。
- AWDL 的控制项照常注册（`debug.be201_awdl_vif_arm` 等），能力位 32 要在手动 arm 之后才通告。
- 所以开机过程和 1.3.2 相同，只多了注册控制项这一步。

**检查：** 两个 ABI 测试通过；1124 个导入符号都在启动内核集合里；布局检查通过；SHA e5fcc9d6。

**EFI（disk1s3）：**
- `AirportItlwm-Tahoe.kext` 改为 1.4.1。`config.plist` 和 07:33 的备份（最后一次成功启动 1.3.2 的配置）相比只有注释不同。
- **回退配置 `EFI/OC/config-fallback.plist`（按用户要求，不再给脚本）：** 唯一的区别是那一项指向 `AirportItlwm-Tahoe-1.3.2.kext`，这是 1.3.2 原样的副本（SHA 7c08e411）。两份配置 ocvalidate 都没有报错。
- 1.4.0 留下的 `AirportItlwm-Tahoe-prev.kext`、它的配置条目和 `BE201-wifi-previous.sh` 都已删除。
- 备份在 `EFI-backups/EFI-before-tahoe-wifi-20261115-080045`。

**登录后的逐步测试（`sudo python3 wifi/kit/awdl_step_test.py`）：**
- 每一行日志和驱动的每一个步骤（`ItlwmAwdlVifStep` 等）都用 F_FULLFSYNC 写进 `outputs/tahoe-wifi/awdl-step-<时间>.log`，就算卡死也能留下最后一步。
- A 段：只打开 AWDL 接口的开关，然后 arm。30 秒内 awdl0 没出现，就关一次再开一次 Wi-Fi。
- B 段：只有 awdl0 稳定 30 秒后才进行，打开跨信道的三项设置。
- 如果卡死：长按电源键，正常开机即可（1.4.1 开机时不会 arm），然后把日志交给 Claude。

### 1.4.1 逐步测试结果：AWDL 建立成功，第一帧 AWDL 管理帧就 panic（2026-11-15 08:04–08:05）

- 日志 `outputs/tahoe-wifi/awdl-step-20261115-080424.log`。
  - A 段打开开关并 arm 之后，Wi-Fi 关闭再打开，wifip2pd 请求创建 awdl0（role 6）。
  - 创建一路走到 ready（native-init → attach → native-start → pool → queues → register → publish → running-state → ready → link-done）。08:05:04 出现 awdl0。
  - 08:05:15.728 日志中断（awdl0 ready 后 11 秒），这时 Mac 正在连 iPhone 热点。
- panic 报告 `Kernel-2026-11-15-080618.panic`：
  - 调用链：`AirportItlwmAWDLInterface::inputActionFrame` → `IO80211Buffer::getCapacity() + 0x8`。
  - 页错误，访问地址 0x10，RAX = 0；在 Wi-Fi 中断的工作循环里。
- **原因：**
  - 25G342 的 `IO80211Buffer` 是虚接口（第 35–53 项）。
  - `IO80211Controller::allocFramePool` 给 `IO80211BufferPool::withOptions` 传了新的参数 true，于是管理帧池在 Tahoe 上是 `IO80211MallocBufferPool`，交出来的是 `IO80211MallocBuffer`，它覆盖了所有这些方法。
  - 驱动按 24G824 的写法直接调用基类的 `getCapacity`/`writeBytes`/`setLength`/`returnBuffer`（24G824 上这些不是虚函数）。基类实现顺着 `+0x10 → +0x10 → +0x10` 去读，malloc 缓冲区里没有这条链，结果在 0x10 处出错。
  - 1.4.0 开机就 arm 了 AWDL，第一帧 AWDL 管理帧进来就 panic，所以进不去系统。
- **核对：**
  - 对 AWDL 代码直接调用的 293 个原生函数，逐个查它们在 25G342 和 24G824 上是否虚函数。只有在 24G824 上不是虚函数、到 25G342 才变成虚函数的，直接调用才会绕过子类的覆盖。
  - 这样的函数里，属于别人对象的只有这 4 个缓冲区方法；其余是我们自己类的虚函数表里本来就有的基类新项，已逐项核对过。

### 独显进不去系统：NVIDIA 驱动的启动保护（不是 Wi-Fi 驱动本身）

- `com.nullmoth.NVRM` 用 NVRAM 变量 `nullmoth-nv-starts` 计数"启动了但没有亮屏"的次数，到 2 次就自动停用，相当于 `-nvoff`。
  - 08:02 开机：计数 1，亮屏后清掉。
  - 08:06 开机：计数 2。08:05 的 Wi-Fi panic 和之后的强制重启把计数推高了。
  - 08:08、08:12、08:19：`NVRMFB: driver off`，没有显示器，WindowServer 在 `CGXMappedDisplayStart` 断言退出。
  - 只有核显能用。
- 现在 NVRAM 里已经没有 `nullmoth-nv-starts`，`nullmoth-nv-ok` = 1，切回独显应该能恢复。NVIDIA 驱动是别的项目，这里没有改动。

## Wi-Fi 1.4.2（缓冲区方法改为虚调用；2026-11-15 08:33 已写入 EFI，等待重启和逐步测试）

- `AirportItlwm/BE201ActionBuffer.hpp`：Tahoe 版把 `IO80211Buffer` 声明为 OSObject 的子类，方法按原生顺序排在第 35–47 项，接收路径改为经虚函数表调用。二进制里可以看到 `*0x140`（getCapacity）、`*0x178`（writeBytes）、`*0x138`（setLength）、`*0x118`（returnBuffer）。Sequoia 版不变。
- `test-awdl-vif-abi-tahoe.py` 新增检查：clang 排出的 `IO80211Buffer` 虚函数表在 35/38/39/40/47 项是对应方法，并且和 25G342 内核集合里 `IO80211Buffer`、`IO80211MallocBuffer` 的同一项一致。导入符号从 603 降到 599：4 个直接调用没有了。两个 ABI 测试都通过。
- AWDL 开机仍然**不启动**（和 1.4.1 一样），先用逐步测试验证：`sudo python3 wifi/kit/awdl_step_test.py`。它现在要求 1.4.2 或更新的版本。
- SHA eaaab8d4。`config-fallback.plist` 仍然指向 1.3.2。备份在 `EFI-backups/EFI-before-tahoe-wifi-20261115-083330`。

### 恢复后的配置（2026-11-15 11:58）

- 用户把 `config.plist` 换回了 06:43 的版本（能开机）。11:54 用它开机：Wi-Fi 1.4.2（`AirportItlwm-Tahoe.kext` 文件夹里已经是 1.4.2）和 Tahoe 蓝牙都正常加载。
- 在这份配置上只改了两处：
  - 麦克风条目 `OhMyDSPACE-037.kext` 换成 `OhMyDSPACE-038.kext`，使用麦克风项目 `Audio/OhMyDSP-ACE/OpenCore-Kernel-Add.plist` 的写法（25.x，0.3.8 已验证）。
  - Wi-Fi 条目的注释改为 1.4.2。
- 其余条目都已经是最新：蓝牙 Tahoe 版（IntelBTPatcher 2.7.0、BlueToolFixup 2.9.0、固件 2.5.3），自动亮度（ThinkBookISHProbe 0.5.3、NativeALSDisplay 1.0.1、ISHLightSensor 1.0.0）。
- `config-fallback.plist` 是用户恢复的那份配置的原样副本。两份配置 ocvalidate 都没有报错。
- 备份在 `EFI-backups/EFI-before-latest-kexts-20261115-115832`。
- 注意：`install_tahoe_wifi.py --install` 会改写条目和回退配置，在这份配置上不要再直接运行它。

### 1.4.2 逐步测试通过（2026-11-16 17:11–17:13）
- 日志 `outputs/tahoe-wifi/awdl-step-20261116-171138.log`：Wi-Fi 关开一次后 awdl0 建立（UP,RUNNING），驱动收到 17856 帧管理帧、发现附近的 Apple 设备，打开跨信道设置（phy2、ROC 0x390024、pause）后也没有 panic。用户确认"测试可以了"。

## Wi-Fi 1.4.3（AWDL 恢复开机默认启用；2026-11-16 18:01 已写入 EFI，等待重启验证）
- `AirportItlwmV2.cpp`：去掉 1.4.1 在 Tahoe 上加的两处限制，be201_awdl_auto 和 be201_awdl_xchan 回到 `ItlAwdlFlag`（25G342 在已验证内核列表里，所以默认开启；开机参数 `=0` 仍可关闭）。上次开机 panic 过时仍会跳过自动启动。
- 测试：test-awdl-vif-abi-tahoe.py（568/505 槽位、599 个导入）、test-wcl-scan-ssid-list.py、test-awdl-vif.py（1472 种调度）都通过。二进制 SHA 5b0db06b（签名后 kext 内 f32c552c）。
- EFI：`AirportItlwm-Tahoe.kext` = 1.4.3；1.4.2 另存为 `AirportItlwm-Tahoe-1.4.2.kext`。`config-fallback.plist` = 刚开机成功的那份 config，唯一差别是 Wi-Fi 条目指向 1.4.2。两份 ocvalidate 均无问题。备份 `EFI-backups/EFI-before-wifi-1.4.3-20261116-180121`。
- 桌面压缩包 `BE201-Tahoe-Drivers-20261116.zip`：AirportItlwm-Tahoe 1.4.3、IntelBTPatcher-Tahoe 2.7.0、BE201BluetoothFirmware-Tahoe 2.5.3、BlueToolFixup-Tahoe 2.9.0（从 EFI 取的安装版本）加说明.txt。

### 1.4.3 结果：开机能进系统，awdl0 自动出现，但隔空投送失败（2026-11-16 18:05–18:08）
- 4 次发送都失败：wifip2pd 报 "Cannot resolve ... because peer not discovered"。Mac 能收到 iPhone 的 AWDL 帧，但 iPhone 一直没确认看到 Mac（"Waiting set routable ... to see this DUT"），没有 "Caching peer"。
- 与 17:13 成功那次的区别：AWDL 配置时的国家码。成功那次是 `CN`，这次一直是 `ZZ`；驱动本身也报 `ZZ`（固件 LAR 没有报出国家，airportd 也没设置过）。逐步测试里的"Wi-Fi 关再开"让固件报出了 `CN`。
- 18:13 手动关开 Wi-Fi 后国家码变为 `CN`，用户确认隔空投送可以传了。

## Wi-Fi 1.4.4（国家码取自已连接网络；2026-11-16 18:20 已写入 EFI，等待重启验证）
- net80211 `ieee80211_recv_probe_resp` 记录信标/探测响应里的 Country IE（`ni_cc`）。关联成功（ASSOC_DONE）时，若固件国家码为 ZZ、且没有 airportd 设置的国家码和 `itlwm_cc`，驱动改用该网络的国家码（`ItlwmBssCountry`），并发出 COUNTRY_CODE_CHANGED；AWDL 在关联时会重新读取国家码。
- 测试：test-awdl-vif-abi-tahoe.py、test-wcl-scan-ssid-list.py、test-awdl-vif.py 通过。二进制 SHA 43c4c500（签名后 d636d036）。
- EFI：`AirportItlwm-Tahoe.kext` = 1.4.4；`config-fallback.plist` 改指向 `AirportItlwm-Tahoe-1.4.3.kext`（今天 18:05 能开机，AWDL 开启，隔空投送需关开一次 Wi-Fi），其余与 config.plist 完全相同；不再引用的 1.4.2 文件夹已删（build/wifi-tahoe 和备份里都有）。ocvalidate 无问题。备份 `EFI-backups/EFI-before-wifi-1.4.4-20261116-182003`。
- 桌面压缩包已更新为 1.4.4。
