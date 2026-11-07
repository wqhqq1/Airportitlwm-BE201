# BE201 1.1.14: AWDL context, link activation as in Linux (default off)

1.1.13 result, boot 16:46: the P2P client context asserted the same 0x2010303E after
LINK_CONFIG activation (0x390309) as IBSS did. One fault, latch held, no AWDL frame. The same
error with two MAC types points at something both share. Comparing with Linux v6.12
__iwl_mvm_mld_assign_vif_chanctx and iwl_mvm_link_changed found one such difference: the
activation command here carried zero rates, beacon interval and EDCA, with mask ACTIVE only.

Change: every LINK_CONFIG for this link now fills all fields, and bring-up follows Linux:
first mask 0 with the PHY id, then ACTIVE|RATES_INFO with active=1. MAC type and
everything else as in 1.1.13, `be201_awdl_ctx=2 be201_awdl_tx=1`.

This is a hypothesis, not a diagnosed cause: 0x2010303E has no public meaning. If it asserts
again, command fields are ruled out and sharing the PHY context remains the suspect; next is the
P2P Device type with ROC. Read order after reboot: ItlwmFwErrors and ItlwmAwdlCtxStage=5,
ItlwmAwdlProbeAction, phone `Posted peer presence` with ItlwmAwdlTxAddr, ItlwmAwdlTxUnicastAck.

Handoff is not used as a pass or fail here. By the user's decision it is observed across
later reboots; its intermittent failure is unexplained. Last good version:
outputs/BE201最新正常版本.md. Verification: scripts/test-awdl-ctx.py and all other suites,
57-unit build. NOT hardware tested.
