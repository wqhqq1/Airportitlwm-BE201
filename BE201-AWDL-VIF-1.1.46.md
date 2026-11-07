# AirportItlwm 1.1.46: peer cache answers off, model back to MacBookPro16,2

1.1.45 results, boot 00:18, user: this Mac could not send AirDrop, only receive; Universal Control worked; Continuity Camera stuck. No fault, no panic. CacheAdds 5, CacheDeletes 5. The family took the answers (`Add cache indication ... peer VALID`), then failed the next step (`sendRealTimeUMI: WARN: Not safe to send UMI`, `Ensemble start Failure, waiting for UMIStatus`), and deleted the peer as inactive within about 3 s, repeatedly (`Uncaching peer ... reason:Due to Inactivity`). sharingd logged no `Send StateMachine` that boot, so no send even started. The link between the delete cycle and the missing send is inferred, not traced: the only driver change from a working 1.1.44 was these answers.

## Change

`debug.be201_awdl_cache_on`, RAM, default 0, replaces `be201_awdl_cache_off`. Off means the same as 1.1.44. The answering code stays for tests.

Config: SystemProductName MacPro7,1 to MacBookPro16,2 at the user's request. Serial, MLB, UUID and ROM unchanged; `config-before-iMac-model.plist` in earlier backups holds this same identity with this model and differs in PlatformInfo only by the name. `config-BE201-awdlsteady-macpro.plist` is the model-only way back. Later kits must stop asserting MacPro7,1 in install.py.

## Still open

Continuity Camera needs UMI to finish, which needs firmware-style sending of the family's UMI, plus the RTP "No network route", llw0 the suspect. Answers must not return by default until the delete cycle is solved. iPhone Mirroring unchanged; the model change does not add a T2.
