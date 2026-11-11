# AirportItlwm 1.1.47: UMI send and result, llw0, both off by default

1.1.46 result: user reports AirDrop send restored. Asked to do both Continuity Camera steps and write to the EFI.

## UMI, read from 24G824

handleUmiTimer calls sendUnicastMI, which calls ioctl type 149 (APPLE80211_IOC_AWDL_OOB_REQUEST), address at +4, length at +0x28, pointer at +0x30 to the template. The driver took this and dropped it: logs on 1.1.45 show "sending UMI#0" and then the 3 s wait for EnsembleUMIStatusDone timing out. The result goes back through reportDataPathEvents case 69, processUnicastAfStatus: address at +0, status at +6, 0 is acked. Status 2 and event 9 follow, then the session starts.

Now: frame as a MIF (subtype 3) unicast to that address with the family's TLVs, on the AP management queue; the TX result is reported as event 69 from a task. Subtype 3 for unicast is inferred from the template's name, not read from a native capture. `debug.be201_awdl_umi`, RAM, default 0. The test also sets `debug.be201_awdl_cache_on`, because the family waits for the cache answer first.

## llw0, read from 24G824

setCOMPANION_SKYWALK_IF_CREATE: operation at +4, 1 creates, 0 deletes; BSD name back at +8, 16 bytes. Native uses prefix llw, id 9, role 2, the same address as awdl0. IO80211SkywalkInterface::start takes the parent's peer manager for role 2. Native derives from the infra class, whose start builds a scan manager and more; this derives from IO80211VirtualInterface, whose init does not depend on role, and reuses awdl0's registration and queues. Vtable 4024 bytes, equal to native IO80211VirtualInterface. Not proven that nothing in the family needs the infra class on this object.

Native firmware tags which interface a received frame is for. Nothing here does, so frames follow ports llw0 has sent from, ICMPv6 goes to both and the rest stays on awdl0. A flow the phone starts toward a port llw0 has not sent from reaches awdl0 and is lost. Whether phone llw frames look different on air is unknown; ItlwmAwdlDataRxBad keeps samples of what does not parse. `debug.be201_awdl_llw`, RAM, default 0; wifip2pd asks once at its start, so the test restarts it. LLW_PARAMS stays accepted and unused.

## Not addressed

The radio stays on the AP channel, while the phone may move in a real time session. iPhone Mirroring unchanged.
