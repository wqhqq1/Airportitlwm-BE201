# BE201 1.1.23: netif pool type, flags chosen at test time

Follow-up to the 1.1.22 arm test (boot 34E54C60, 21:06:57).

## What the test showed

No panic, and the system stayed up. The kept-object fix works. Steps reached publish; after 10 s the create returned NotReady, FailedStage 5, RegistrationError 0. `ifconfig` has no awdl0, and no IOSkywalkNetworkBSDClient is attached. The object does carry `BSD Name` = awdl0, which the client's `start` writes, so `start` ran and then gave up silently. Its next fallible steps are registerNexusControllerProvider and `kern_nexus_controller_alloc_net_provider_instance`. Native gives no errno here, so which one failed is not observed.

## Suspect

1.1.21 changed the pool to type 0, copied from AppleConvergedIPCSkywalkInterface. That driver registers through registerInterfaceWithQueues, a kernel pipe, not a netif. In `IOSkywalkPacketBufferPool::initWithName`, type 0 selects a quantum pool. Native `AppleBCMWLANSkywalkPacketPool::initWithName` passes type 1. That mistake was mine. It is the prime suspect, not proven.

Native BCM pool flags were not found. IOUserNetworkPacketBufferPool masks its flags with 0x30001606, so bit 0 stays clear; bit 0 maps to kernel pool flag 0x20. reAWDL set flags 1 on Sonoma.

## Changes

Pool type is 1. New RAM-only sysctl `debug.be201_awdl_vif_poolflags` (default 0, only bit 0 is used) picks the flags before arming, so trying the other value takes a reboot but no EFI write. Queue arguments stay as they were; BCM's receive submission queue also passes 1 there.

## Verification

21 suites pass; the lifecycle test now asserts pool type 1 and the flags value. `kmutil libraries` resolves imports. Not hardware tested. The nexus may still refuse for another reason, and reaching awdl0 exposes new native paths that may crash.
