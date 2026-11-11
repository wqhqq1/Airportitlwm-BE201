# AirportItlwm 1.1.68: llw0 back to a test switch, UMI stays on

## 1.1.67 result, boot 21:29, 2026-11-08

- **Camera and Sidecar:** llw0 was fully up:
  - stage 6, `xflags=400<LOWAT>`;
  - netif nexus attached, agent Skywalk/NetIf with flags 0x4c3;
  - FeatureFlags 0x10000 (the native value from 1.1.51).

  Still, ContinuityCaptureAgent (21:37:29) and SidecarRelay (21:39:56) logged `nw_path_flow_get_nexus_instance ... interface: llw0, assigned returned false`. The on-demand bit was not the cause. llw0 never carried a frame, and its SIOCADDMULTI returns EOPNOTSUPP. Why the netif agent does not assign the flow needs root `skywalkctl netstat -s`.
- **Universal Control:** it broke. Its Rapport link flags are `< BLE AWDL ForceAWDL NoiWiFi Ensemble >`. From 21:43, wifip2pd logged "Failed to set traffic registration for ensemble ... General I/O error" (0xE00002CA) for UniversalControl sessions. The user turned off `debug.be201_awdl_llw` (UMI stayed on), and Universal Control recovered. So llw0 being on is the cause, and UMI is not.
- **Solo AWDL (1.1.66) before the hotspot join at 21:34:40:** Phy2QSent 8, Phy2QDone 0, Phy2QDrop 64. Its frames never completed.

## Change

- `startAWDLAuto` keeps UMI on (property ItlwmAwdlUmiDefault).
- llw0 is no longer turned on. It is off by default, as before 1.1.67, and the RAM switch `debug.be201_awdl_llw` remains for tests.
- test-awdl-ba checks that UMI is on, llw0 is not, and both are set after the panic check.
