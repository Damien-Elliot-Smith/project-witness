"""Tests for Stack Selfcheck v0.1.1 legacy documentation compatibility.

The four early frozen components may omit exactly the documentation files their
recorded legacy profile permits. Every other component must still carry the full
documentation set. False or unknown legacy claims are refused, and every
allowance is recorded honestly and re-derived by the verifier.
"""

import os

from stack_selfcheck_lib import (canonical, report as report_mod, verifier,
                                  versions)
from stack_selfcheck_lib.errors import (CheckError, VerifyError,
                                        COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED)
from tests._helpers import TempCase

PROFILE = versions.LEGACY_DOCUMENTATION_PROFILE

# The exact real allowances, mirrored from the registry.
_LEGACY = {
    "sentinel_core_v022": ["KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"],
    "histor_lite_v012": ["RELEASE_COMMANDS.md"],
    "case_bundle_v011": ["RELEASE_COMMANDS.md"],
    "atlas_red_blue_pack_v01": ["KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"],
}


class TestLegacyDocumentation(TempCase):
    def _legacy_inventory(self, **kw):
        omit_docs = {cid: docs for cid, docs in _LEGACY.items()}
        profiles = {cid: PROFILE for cid in _LEGACY}
        return self.inventory(omit_docs=omit_docs, legacy_profiles=profiles, **kw)

    # 1. legacy component allowed missing exact legacy docs
    def test_legacy_components_allowed_missing_exact_docs(self):
        report, _ = report_mod.build_selfcheck_report(self._legacy_inventory())
        self.assertEqual(report["stack_selfcheck_status"], "STACK_SELFCHECK_PASSED")
        self.assertEqual(report["documentation_boundary_status"],
                         "DOCUMENTATION_BOUNDARY_VERIFIED")

    # 2. legacy allowance recorded in report (honestly, with exact missing docs)
    def test_legacy_allowance_recorded(self):
        report, _ = report_mod.build_selfcheck_report(self._legacy_inventory())
        recs = {r["component_id"]: r
                for r in report["legacy_documentation_allowances"]}
        self.assertEqual(set(recs), set(_LEGACY))
        for cid, docs in _LEGACY.items():
            rec = recs[cid]
            self.assertEqual(rec["legacy_documentation_profile"], PROFILE)
            self.assertTrue(rec["legacy_documentation_allowance_used"])
            self.assertEqual(sorted(rec["missing_docs_allowed"]), sorted(docs))
            self.assertTrue(rec["reason"])
        # checked_components marks exactly these as legacy-accepted
        marked = {c["component_id"] for c in report["checked_components"]
                  if c["check_status"] == COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED}
        self.assertEqual(marked, set(_LEGACY))

    # 2b. the recorded output verifies end-to-end
    def test_legacy_output_verifies(self):
        out = self.build_output(self._legacy_inventory())
        self.assertTrue(verifier.verify(out).ok)

    # 3. unknown component claims legacy status -> refused
    def test_unknown_component_claims_legacy_refused(self):
        # coordinator_workflow_v03 is NOT a recognised legacy component
        inv = self.inventory(legacy_profiles={"coordinator_workflow_v03": PROFILE})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 3b. a recognised legacy id with a fabricated profile string -> refused
    def test_false_legacy_profile_refused(self):
        inv = self.inventory(
            omit_docs={"histor_lite_v012": ["RELEASE_COMMANDS.md"]},
            legacy_profiles={"histor_lite_v012": "totally_made_up_profile"})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 4. newer (non-legacy) component missing docs -> refused
    def test_newer_component_missing_docs_refused(self):
        inv = self.inventory(omit_docs={"stack_verifier_v01": ["RELEASE_COMMANDS.md"]})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 4b. a legacy component that omits a doc WITHOUT declaring the profile
    #     is still refused (the allowance is opt-in, never automatic).
    def test_legacy_id_without_declared_profile_refused(self):
        inv = self.inventory(omit_docs={"sentinel_core_v022": ["KNOWN_LIMITATIONS.md"]})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 5. legacy component missing a doc NOT allowed by its profile -> refused
    def test_legacy_component_missing_non_allowed_doc_refused(self):
        # histor_lite_v012 may omit only RELEASE_COMMANDS.md; dropping README.md
        # (never allowed) must still fail.
        inv = self.inventory(
            omit_docs={"histor_lite_v012": ["RELEASE_COMMANDS.md", "README.md"]},
            legacy_profiles={"histor_lite_v012": PROFILE})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 5b. a legacy CLI file is never covered by the allowance
    def test_legacy_cli_file_still_required(self):
        inv = self.inventory(
            omit_docs={"sentinel_core_v022":
                       ["KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md", "selfcheck.py"]},
            legacy_profiles={"sentinel_core_v022": PROFILE})
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    # 6. a declared-but-unused legacy profile is recorded truthfully (not silent)
    def test_declared_but_unused_allowance_recorded(self):
        # sentinel keeps all its docs but still declares the profile.
        inv = self.inventory(legacy_profiles={"sentinel_core_v022": PROFILE})
        report, _ = report_mod.build_selfcheck_report(inv)
        recs = {r["component_id"]: r
                for r in report["legacy_documentation_allowances"]}
        self.assertIn("sentinel_core_v022", recs)
        self.assertFalse(recs["sentinel_core_v022"]["legacy_documentation_allowance_used"])
        self.assertEqual(recs["sentinel_core_v022"]["missing_docs_allowed"], [])
        # because the allowance was not used, it is NOT marked legacy-accepted
        marked = {c["component_id"] for c in report["checked_components"]
                  if c["check_status"] == COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED}
        self.assertNotIn("sentinel_core_v022", marked)


class TestLegacyVerifierHonesty(TempCase):
    """The verifier independently re-derives entitlement and rejects tampering."""

    def _out(self):
        omit_docs = {cid: docs for cid, docs in _LEGACY.items()}
        profiles = {cid: PROFILE for cid in _LEGACY}
        return self.build_output(self.inventory(omit_docs=omit_docs,
                                                 legacy_profiles=profiles))

    def _load(self, out):
        return canonical.load_json(os.path.join(out, "stack_selfcheck_report.json"))

    def _save(self, out, rep):
        canonical.write_canonical(
            os.path.join(out, "stack_selfcheck_report.json"), rep)
        self.rebuild_checksums(out)

    def test_clean_legacy_output_verifies(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_allowance_exceeding_registry_fails(self):
        out = self._out()
        rep = self._load(out)
        for r in rep["legacy_documentation_allowances"]:
            if r["component_id"] == "histor_lite_v012":
                r["missing_docs_allowed"] = ["RELEASE_COMMANDS.md", "README.md"]
        self._save(out, rep)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_allowance_for_non_legacy_component_fails(self):
        out = self._out()
        rep = self._load(out)
        rep["legacy_documentation_allowances"].append({
            "component_id": "stack_verifier_v01",
            "legacy_documentation_profile": PROFILE,
            "legacy_documentation_allowance_used": True,
            "missing_docs_allowed": ["RELEASE_COMMANDS.md"],
            "reason": "component frozen before documentation convention",
        })
        rep["legacy_documentation_allowances"].sort(key=lambda r: r["component_id"])
        self._save(out, rep)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_used_flag_inconsistent_fails(self):
        out = self._out()
        rep = self._load(out)
        for r in rep["legacy_documentation_allowances"]:
            if r["component_id"] == "histor_lite_v012":
                r["legacy_documentation_allowance_used"] = False
        self._save(out, rep)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_marking_without_record_fails(self):
        out = self._out()
        rep = self._load(out)
        # mark a non-legacy component as legacy-accepted with no matching record
        rep["checked_components"][0]["check_status"] = \
            COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED
        self._save(out, rep)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_missing_documentation_boundary_status_fails(self):
        out = self._out()
        rep = self._load(out)
        rep["documentation_boundary_status"] = "SOMETHING_ELSE"
        self._save(out, rep)
        with self.assertRaises(VerifyError):
            verifier.verify(out)
