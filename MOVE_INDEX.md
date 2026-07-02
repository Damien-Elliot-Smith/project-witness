# Move Index - Roadmap Steps 1-70

Every completed Roadmap One step from 1 to 70 mapped to the artifact that fulfils it, and where
that artifact now lives: **W** = `Project_Witness_WORKING_STACK/`, **A** =
`Project_Witness_ARCHIVE/`.

Some steps are *freeze* states of a component already built in an earlier step
(e.g. "Freeze Sentinel Core"). Those are not separate folders; they are the
frozen state of their component, noted as "(freeze of …)".

| # | Roadmap move | Artifact | Where |
|---:|---|---|---|
| 1 | Build Sentinel Core v0.2.2 | sentinel_core_v022 | W `src/01_sentinel_core` |
| 2 | Freeze Sentinel Core | (freeze of sentinel_core_v022) | W `src/01_sentinel_core/_frozen` |
| 3 | Build Sentinel Red/Blue Pack | sentinel_red_blue_pack_v01 | A `02_red_blue_packs` |
| 4 | Build Histor-lite Importer | histor_lite_v012 | W `src/02_histor_lite` |
| 5 | Build Case Bundle | case_bundle_v011 | A `01_superseded_component_versions/Case bundle` |
| 6 | Build Coordinator Workflow | coordinator_workflow_v018 | A `01_superseded_component_versions/Coordinator workflow` |
| 7 | Build Companion CLI | companion_cli_v01 | A `01_superseded_component_versions/Companion` |
| 8 | Build Full Workflow Red/Blue Pack | project_witness_workflow_red_blue_pack_v01 | A `02_red_blue_packs` |
| 9 | Build Aletheia Evidence Bundle | aletheia_evidence_bundle_v01 | W `src/03_aletheia_evidence_bundle` |
| 10 | Build ODIN Claim Reasoner | odin_claim_reasoner_v01 | W `src/05_odin_claim_reasoner` |
| 11 | Build ODIN Red/Blue Pack | odin_red_blue_pack_v01 | A `02_red_blue_packs` |
| 12 | Freeze ODIN Red/Blue Pack | (freeze of odin_red_blue_pack_v01) | A `02_red_blue_packs` |
| 13 | Build Aletheia to ODIN Bridge | aletheia_odin_bridge_v01 | W `src/04_aletheia_odin_bridge` |
| 14 | Build Evidence Reasoning Demo | evidence_reasoning_demo_v01 | W `src/16_evidence_reasoning_demo` |
| 15 | Freeze Evidence Reasoning Demo | (freeze of evidence_reasoning_demo_v01) | W `src/16_evidence_reasoning_demo/_frozen` |
| 16 | Build Histor-lite Aletheia Importer | histor_lite_aletheia_importer_v01 | W `src/06_histor_aletheia_importer` |
| 17 | Build Histor-lite ODIN Importer | histor_lite_odin_importer_v01 | W `src/07_histor_odin_importer` |
| 18 | Build Case Bundle v0.2 | case_bundle_v02 | W `src/08_case_bundle_v02` |
| 19 | Build Coordinator Workflow v0.2 | coordinator_workflow_v02 | A `01_superseded_component_versions` |
| 20 | Build Companion CLI v0.2 | companion_cli_v02 | A `01_superseded_component_versions` |
| 21 | Build Atlas Registry v0.1 | atlas_registry_v01 | W `src/09_atlas_registry` |
| 22 | Build Atlas Release Gate | atlas_release_gate_v01 | W `src/10_atlas_release_gate` |
| 23 | Build Atlas Red/Blue Pack | atlas_red_blue_pack_v01 | A `02_red_blue_packs` |
| 24 | Connect Coordinator to Atlas | coordinator_workflow_v03 | A `01_superseded_component_versions` |
| 25 | Connect Companion to Atlas Terms | companion_cli_v03 | A `01_superseded_component_versions/Companion CLI v0.3` |
| 26 | Build Unified Case Manifest v0.1 | unified_case_manifest_v01 | W `src/13_unified_case_manifest` |
| 27 | Build Stack Verifier v0.1 | stack_verifier_v01 | W `src/14_stack_verifier` |
| 28 | Build Stack Selfcheck v0.1 | stack_selfcheck_v01 | A `01_superseded_component_versions` |
| 29 | Build Stack Red/Blue Pack v0.2 | stack_red_blue_pack_v02 | A `02_red_blue_packs` |
| 30 | Freeze Connected Demo v0.1 | connected_demo_v01 | W `src/17_connected_demo` |
| 31 | Build Beginner Runbook | beginner_runbook_v01 | A `03_review_and_documentation` |
| 32 | Build One-Command Demo Script | one_command_demo_script_v01 | W `src/18_one_command_demo` |
| 33 | Build Demo Output Bundle | demo_output_bundle_v01 | A `03_review_and_documentation` |
| 34 | Build Architecture Diagram | architecture_diagram_v01 | A `03_review_and_documentation` |
| 35 | Build Master Known Limitations | master_known_limitations_v01 | A `03_review_and_documentation` |
| 36 | Build Threat Model v0.1 | threat_model_v01 | A `03_review_and_documentation` |
| 37 | Build External Review Pack v0.1 | external_review_pack_v01 | A `03_review_and_documentation` |
| 38 | Build Hostile Review Prompt Pack | hostile_review_prompt_pack_v01 | A `03_review_and_documentation` |
| 39 | Build Response-to-Review Ledger | response_to_review_ledger_v01 | A `03_review_and_documentation` |
| 40 | Freeze Local Demo Pack | project_witness_local_demo_pack_v01 | A `05_large_review_bundles` |
| 41 | Run Full-Stack Red Team Round 1 | full_stack_red_team_round_1_v01 | A `04_hardening_rounds` |
| 42 | Run Full-Stack Blue Team Repair Round 1 | full_stack_blue_team_repair_round_1_v01 (+ repaired demo pack) | A `04_hardening_rounds` |
| 43 | Run Full-Stack Red Team Round 2 | full_stack_red_team_round_2_v01 | A `04_hardening_rounds` |
| 44 | Clean Full-Stack Documentation | full_stack_documentation_clean_v01 | A `04_hardening_rounds` |
| 45 | Freeze All Component Versions | full_stack_component_version_freeze_v01 | W `verify/` |
| 46 | Build Independent Verification Script | independent_verification_script_v01 | W `verify/` |
| 47 | Build Example Reviewer Walkthrough | example_reviewer_walkthrough_v01 | A `05_large_review_bundles` |
| 48 | Build Human-Readable Reports | human_readable_reports_v01 | A `05_large_review_bundles` |
| 49 | Clean Error Messages | move49_clean_error_messages | A `04_hardening_rounds` |
| 50 | Freeze Local v1 Candidate | local_v1_candidate_v01 | W `freeze_record/` |
| 51 | Build Termux Run Instructions | termux_run_instructions_v01 | W `freeze_record/` |
| 52 | Linux Desktop Run Instructions | LINUX_DESKTOP_RUN_INSTRUCTIONS.md + `tools/check_linux_desktop_instructions.sh` | W (repo root) |
| 53 | Windows Notes | WINDOWS_NOTES.md + `tools/check_windows_notes.sh` | W (repo root) |
| 54 | Clean GitHub Repository Structure | README.md, REPOSITORY_STRUCTURE.md, LICENSE + `tools/check_repository_structure.sh` | W (repo root) |
| 55 | Build Private Reviewer Package | PRIVATE_REVIEWER_PACKAGE.md, PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md + `tools/check_private_reviewer_package.sh` | W (repo root) |
| 56 | Build Public-Facing Short Explanation | PUBLIC_EXPLANATION.md + `tools/check_public_explanation.sh` | W (repo root) |
| 57 | Build Five-Minute Demo Script | FIVE_MINUTE_DEMO_SCRIPT.md + `tools/check_five_minute_demo_script.sh` | W (repo root) |
| 58 | Run Reviewer Feedback Round | REVIEWER_FEEDBACK_ROUND.md, REVIEWER_FEEDBACK_LEDGER.md, REVIEWER_FEEDBACK_TRIAGE.md + `tools/check_reviewer_feedback_round.sh` | W (repo root) |
| 59 | Repair Release Blockers | RELEASE_BLOCKER_REGISTER.md, RELEASE_BLOCKER_REPAIR_LEDGER.md + `tools/check_release_blockers.sh` | W (repo root) |
| 60 | Freeze Local v1 Release | LOCAL_V1_RELEASE.md, freeze_record/local_v1_release_v01/ + `tools/check_local_v1_release.sh` | W (repo root + `freeze_record/`) |
| 61 | Decide Next Product Direction | move_61_next_direction_part_two_v01 | final package / releases |
| 62 | Add Second Sentinel Action | move_62_create_text_file_action_v01 | final package / releases |
| 63 | Add Additional Evidence Types | move_63_additional_evidence_types_v01 | final package / releases |
| 64 | Build Signing Design Document | move_64_signing_design_document_v01 | final package / releases |
| 65 | Build Signing Prototype | move_65_signing_prototype_v01 | final package / releases |
| 66 | Build External Anchoring Prototype | move_66_external_anchoring_prototype_v01 | final package / releases |
| 67 | Build Simple Local Web UI | move_67_simple_local_web_ui_v01 | final package / releases |
| 68 | Plan Android Wrapper | move_68_android_wrapper_plan_v01 | final package / releases |
| 69 | Plan Windows Wrapper | move_69_windows_wrapper_plan_v01 | final package / releases |
| 70 | Run Project Witness Local v1.0 Final Review | move_70_local_v1_final_review_v01 | `releases/roadmap_one_complete/move_70_final/` |

---

## Status

- Roadmap One complete: Steps 1-70.
- Complete as a local review/demo stack.
- Not production-ready.
- Does not prove external truth.
- No external reviewer approval is claimed.
- Move 65 signing is test-only.
- Move 66 anchoring is local simulation only.
- Move 67 UI is read-only.
- Moves 68 and 69 are planning-only.

Status exact marker: Roadmap One complete as a local review/demo stack. Not production-ready. Does not prove external truth.
