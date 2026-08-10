#!/usr/bin/env python3
"""Move 82 build-provenance record.

Build facts ONLY. This record must never carry bundle verdicts, check
results or any verifier report content -- that is Move 83 and is out of
scope here. The test for a proposed field is simple: if it would describe
what a bundle IS or what a verification FOUND, it does not belong.

Two contract points worth stating explicitly:

* There is no transcript_sha256 field. A transcript cannot be hashed until
  it is complete, so embedding its hash in a record written earlier in the
  same run would be circular. The record carries transcript_name only; the
  completed transcript receives its own independent sidecar afterwards.

* test_level may be at most `fixture_tested`. Adoption-tested status is
  NOT a self-declared property of a build record: it is established
  externally by a complete successful gate run plus the preserved
  transcript and its sidecar.
"""

import argparse
import json
import os
import sys


SCHEMA_VERSION = "witness-build-provenance/1"
RECORD_TYPE = "build_provenance"

# Ordered weakest to strongest. `adoption_tested` and `publicly_releasable`
# are deliberately ABSENT: a build record cannot confer them on itself.
TEST_LEVELS = ("compiled", "format_validated", "smoke_tested",
               "fixture_tested")

REQUIRED_FIELDS = (
    "architecture",
    "baseline_name",
    "baseline_sha256",
    "binary_name",
    "binary_sha256",
    "binary_size_bytes",
    "build_argv",
    "build_environment",
    "build_profile",
    "cargo_package_version",
    "cargo_version",
    "executable_format",
    "limitations",
    "record_type",
    "reported_version",
    "runtime_dependencies",
    "rustc_host",
    "rustc_version",
    "schema_version",
    "source_candidate_name",
    "source_candidate_sha256",
    "target_triple",
    "test_level",
    "transcript_name",
)

# Every provenance record must carry these three honest limitations.
REQUIRED_LIMITATIONS = (
    "this is an Android/Termux binary, not a general Linux binary",
    "no runtime evidence exists for Linux or Windows",
    "separate builds are not claimed to be byte-reproducible",
)

FORBIDDEN_FIELDS = (
    # Move 83 territory: verifier report content
    "verdict", "reason_code", "stage", "checks", "check_results",
    "bundle_hash", "bundle_verdict", "report", "findings",
    # circular by construction
    "transcript_sha256",
)


class ProvenanceError(Exception):
    """Deterministic, message-only provenance failure."""


def _is_hex64(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


def build_record(facts):
    """Assemble the record from established facts. `facts` must already
    contain only measured values."""
    record = dict(facts)
    record["schema_version"] = SCHEMA_VERSION
    record["record_type"] = RECORD_TYPE
    validate(record)
    return record


def validate(record):
    """Fail closed on anything unestablished, overclaimed or out of
    scope."""
    if not isinstance(record, dict):
        raise ProvenanceError("record is not an object")
    for field in FORBIDDEN_FIELDS:
        if field in record:
            raise ProvenanceError(
                "forbidden field present: %s" % field)
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise ProvenanceError(
            "missing required field(s): %s" % ", ".join(sorted(missing)))
    if record["schema_version"] != SCHEMA_VERSION:
        raise ProvenanceError("wrong schema_version")
    if record["record_type"] != RECORD_TYPE:
        raise ProvenanceError("wrong record_type")

    for field in ("binary_sha256", "source_candidate_sha256",
                  "baseline_sha256"):
        if not _is_hex64(record[field]):
            raise ProvenanceError(
                "%s is not a lowercase 64-character hex digest" % field)

    if record["test_level"] not in TEST_LEVELS:
        raise ProvenanceError(
            "test_level must be one of %s (adoption status is established "
            "externally by the gate transcript, never self-declared)"
            % ", ".join(TEST_LEVELS))

    if record["build_profile"] != "release":
        raise ProvenanceError(
            "the preserved portable artefact must be a release build")

    size = record["binary_size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ProvenanceError("binary_size_bytes must be a positive int")

    argv = record["build_argv"]
    if not isinstance(argv, list) or not argv \
            or not all(isinstance(a, str) and a for a in argv):
        raise ProvenanceError(
            "build_argv must be a non-empty array of non-empty strings")

    deps = record["runtime_dependencies"]
    if not isinstance(deps, list) \
            or not all(isinstance(d, str) and d for d in deps):
        raise ProvenanceError(
            "runtime_dependencies must be an array of non-empty strings")
    if deps != sorted(deps):
        raise ProvenanceError(
            "runtime_dependencies must be deterministically sorted")
    if len(set(deps)) != len(deps):
        raise ProvenanceError("runtime_dependencies contains duplicates")

    limits = record["limitations"]
    if not isinstance(limits, list) or not limits:
        raise ProvenanceError("limitations must be a non-empty array")
    for required in REQUIRED_LIMITATIONS:
        if required not in limits:
            raise ProvenanceError(
                "limitations must include: %s" % required)

    env = record["build_environment"]
    if not isinstance(env, dict):
        raise ProvenanceError("build_environment must be an object")

    for field in ("binary_name", "reported_version", "cargo_package_version",
                  "source_candidate_name", "baseline_name", "target_triple",
                  "architecture", "executable_format", "cargo_version",
                  "rustc_version", "rustc_host", "transcript_name"):
        value = record[field]
        if not isinstance(value, str) or value.strip() == "":
            raise ProvenanceError("%s must be a non-empty string" % field)

    # The authorised target is enforced by CROSS-FIELD consistency, so a
    # record describing an x86_64 Linux build can never validate.
    required_exact = {
        "target_triple": "aarch64-linux-android",
        "rustc_host": "aarch64-linux-android",
        "architecture": "aarch64",
        "executable_format": "ELF64",
        "build_profile": "release",
        "reported_version": "0.0.8-step79-diagnostics",
        "cargo_package_version": "0.0.8",
    }
    for field, want in sorted(required_exact.items()):
        if record[field] != want:
            raise ProvenanceError(
                "%s is %r; the authorised target requires %r"
                % (field, record[field], want))
    env = record["build_environment"]
    if env.get("endianness") != "little":
        raise ProvenanceError("endianness must be little for the "
                              "authorised target")
    if env.get("elf_type") != "DYN":
        raise ProvenanceError("elf_type must be DYN for the authorised "
                              "native Termux release build")
    return True


def canonical_bytes(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sidecar_bytes(digest, basename):
    """Standard sidecar content: <sha256><two spaces><basename><newline>."""
    return ("%s  %s\n" % (digest, basename)).encode("utf-8")


class PublishError(Exception):
    """Deterministic, message-only publication failure."""


def publish(binary_path, record_path, out_dir, final_base):
    """Publish the release binary, the provenance record and a SHA-256
    sidecar for each, atomically with respect to failure.

    Every step is rolled back on ANY failure -- copy, chmod, hashing,
    validation or verification -- so a failed publication leaves the
    output directory exactly as empty as it began. Nothing is treated as
    published until every post-publication check has passed."""
    written = []

    def _rollback():
        for path in reversed(written):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

    try:
        if not os.path.isdir(out_dir):
            raise PublishError("output directory does not exist")
        existing = os.listdir(out_dir)
        if existing:
            raise PublishError("output directory is not empty")

        final_bin = os.path.join(out_dir, final_base)
        final_rec = os.path.join(out_dir, final_base + ".provenance.json")
        final_bin_sc = final_bin + ".sha256"
        final_rec_sc = final_rec + ".sha256"

        # 1. binary
        with open(binary_path, "rb") as src:
            data = src.read()
        with open(final_bin, "wb") as dst:
            dst.write(data)
        written.append(final_bin)
        os.chmod(final_bin, 0o755)

        # 2. provenance record
        with open(record_path, "rb") as src:
            record_raw = src.read()
        with open(final_rec, "wb") as dst:
            dst.write(record_raw)
        written.append(final_rec)

        # 3. sidecars
        bin_digest = sha256_file(final_bin)
        with open(final_bin_sc, "wb") as dst:
            dst.write(sidecar_bytes(bin_digest, os.path.basename(final_bin)))
        written.append(final_bin_sc)
        rec_digest = sha256_file(final_rec)
        with open(final_rec_sc, "wb") as dst:
            dst.write(sidecar_bytes(rec_digest, os.path.basename(final_rec)))
        written.append(final_rec_sc)

        # 4. post-publication verification
        # Re-read the COPIED file from disk: validating the staged bytes
        # we happen to still hold would not prove what was published.
        with open(final_rec, "rb") as handle:
            copied_raw = handle.read()
        if copied_raw != record_raw:
            raise PublishError("copied provenance differs from the staged "
                               "record")
        try:
            record = json.loads(copied_raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise PublishError("published provenance is not readable JSON")
        record_raw = copied_raw
        validate(record)
        if record["binary_sha256"] != bin_digest:
            raise PublishError(
                "published binary hash does not match binary_sha256 in "
                "provenance")
        if canonical_bytes(record) != record_raw:
            raise PublishError("published provenance is not canonical")
        for sidecar, subject, digest in (
                (final_bin_sc, final_bin, bin_digest),
                (final_rec_sc, final_rec, rec_digest)):
            with open(sidecar, "rb") as handle:
                content = handle.read()
            if content != sidecar_bytes(digest, os.path.basename(subject)):
                raise PublishError("sidecar content is not as expected")
            if sha256_file(subject) != digest:
                raise PublishError("subject hash changed after publication")

        # 5. exactly the expected four files, nothing else
        present = sorted(os.listdir(out_dir))
        expected = sorted(os.path.basename(p) for p in
                          (final_bin, final_rec, final_bin_sc, final_rec_sc))
        if present != expected:
            raise PublishError(
                "output directory does not contain exactly the four "
                "expected files")
        return {
            "binary": os.path.basename(final_bin),
            "binary_sha256": bin_digest,
            "provenance": os.path.basename(final_rec),
            "provenance_sha256": rec_digest,
        }
    except (PublishError, ProvenanceError, OSError) as exc:
        _rollback()
        raise PublishError(str(exc))


def assemble_from_files(inspect_json, build_json, extras):
    """Assemble provenance facts from the inspector's JSON file and the
    build tool's JSON facts. This is the EXACT path the gate uses, so it
    is directly testable end to end."""
    try:
        with open(inspect_json, encoding="utf-8") as handle:
            ins = json.load(handle)
    except (ValueError, OSError):
        raise ProvenanceError("inspector JSON is not readable JSON")
    if not isinstance(ins, dict):
        raise ProvenanceError("inspector JSON is not an object")
    try:
        with open(build_json, encoding="utf-8") as handle:
            bld = json.load(handle)
    except (ValueError, OSError):
        raise ProvenanceError("build facts JSON is not readable JSON")
    if not isinstance(bld, dict):
        raise ProvenanceError("build facts JSON is not an object")

    binary = extras["binary_path"]
    if not os.path.isfile(binary):
        raise ProvenanceError("binary path is not a regular file")
    facts = {
        "binary_name": os.path.basename(binary),
        "binary_sha256": sha256_file(binary),
        "binary_size_bytes": ins.get("binary_size_bytes"),
        "reported_version": extras["reported_version"],
        "cargo_package_version": extras["cargo_package_version"],
        "source_candidate_name": extras["source_candidate_name"],
        "source_candidate_sha256": extras["source_candidate_sha256"],
        "baseline_name": extras["baseline_name"],
        "baseline_sha256": extras["baseline_sha256"],
        "target_triple": bld.get("rustc_host"),
        "architecture": ins.get("architecture"),
        "executable_format": ins.get("executable_format"),
        "build_profile": bld.get("build_profile"),
        "cargo_version": bld.get("cargo_version"),
        "rustc_version": bld.get("rustc_version"),
        "rustc_host": bld.get("rustc_host"),
        "build_argv": bld.get("build_argv"),
        "build_environment": {
            "cargo_home": "ephemeral-per-run",
            "external_crates": 0,
            "elf_type": ins.get("elf_type"),
            "endianness": ins.get("endianness"),
            "interpreter": ins.get("interpreter"),
        },
        "runtime_dependencies": sorted(ins.get("runtime_dependencies") or []),
        "test_level": extras["test_level"],
        "transcript_name": extras["transcript_name"],
        "limitations": list(REQUIRED_LIMITATIONS),
    }
    return build_record(facts)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 82 build-provenance record")
    parser.add_argument("--facts", default=None,
                        help="absolute path to a JSON object of measured "
                             "facts")
    parser.add_argument("--inspect-json", default=None)
    parser.add_argument("--build-json", default=None)
    parser.add_argument("--binary", default=None)
    parser.add_argument("--reported-version", default=None)
    parser.add_argument("--cargo-package-version", default="0.0.8")
    parser.add_argument("--source-candidate-name", default=None)
    parser.add_argument("--source-candidate-sha256", default=None)
    parser.add_argument("--baseline-name", default=None)
    parser.add_argument("--baseline-sha256", default=None)
    parser.add_argument("--test-level", default="fixture_tested")
    parser.add_argument("--transcript-name", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--publish-binary", default=None)
    parser.add_argument("--publish-record", default=None)
    parser.add_argument("--publish-dir", default=None)
    parser.add_argument("--publish-base", default=None)
    args = parser.parse_args(argv)

    # ---- publication mode -------------------------------------------
    if args.publish_dir is not None:
        for value, what in ((args.publish_binary, "--publish-binary"),
                            (args.publish_record, "--publish-record"),
                            (args.publish_dir, "--publish-dir")):
            if not value or not os.path.isabs(value):
                print("usage error: %s must be an absolute path" % what)
                return 2
        if not args.publish_base:
            print("usage error: --publish-base is required")
            return 2
        try:
            result = publish(args.publish_binary, args.publish_record,
                             args.publish_dir, args.publish_base)
        except PublishError as exc:
            print("PUBLISH: FAIL (%s)" % exc)
            return 1
        sys.stdout.write(json.dumps(result, sort_keys=True,
                                    separators=(",", ":"),
                                    ensure_ascii=False) + "\n")
        print("PUBLISH: PASS")
        return 0

    # ---- assembly mode ----------------------------------------------
    if args.inspect_json is not None:
        required = {
            "--build-json": args.build_json,
            "--binary": args.binary,
            "--reported-version": args.reported_version,
            "--source-candidate-name": args.source_candidate_name,
            "--source-candidate-sha256": args.source_candidate_sha256,
            "--baseline-name": args.baseline_name,
            "--baseline-sha256": args.baseline_sha256,
            "--transcript-name": args.transcript_name,
        }
        missing = sorted(k for k, v in required.items() if not v)
        if missing:
            print("usage error: missing %s" % ", ".join(missing))
            return 2
        extras = {
            "binary_path": args.binary,
            "reported_version": args.reported_version,
            "cargo_package_version": args.cargo_package_version,
            "source_candidate_name": args.source_candidate_name,
            "source_candidate_sha256": args.source_candidate_sha256,
            "baseline_name": args.baseline_name,
            "baseline_sha256": args.baseline_sha256,
            "test_level": args.test_level,
            "transcript_name": args.transcript_name,
        }
        try:
            record = assemble_from_files(args.inspect_json, args.build_json,
                                         extras)
        except ProvenanceError as exc:
            print("PROVENANCE: FAIL (%s)" % exc)
            return 1
        raw = canonical_bytes(record)
        if args.out is not None:
            if not os.path.isabs(args.out):
                print("usage error: --out must be an absolute path")
                return 2
            with open(args.out, "wb") as handle:
                handle.write(raw)
        else:
            sys.stdout.buffer.write(raw)
        print("PROVENANCE: PASS")
        return 0

    # ---- validate-a-facts-file mode ---------------------------------
    if args.facts is None:
        print("usage error: one of --facts, --inspect-json or "
              "--publish-dir is required")
        return 2
    if not os.path.isabs(args.facts) or not os.path.isfile(args.facts):
        print("usage error: --facts must be an absolute regular file")
        return 2
    try:
        with open(args.facts, encoding="utf-8") as handle:
            facts = json.load(handle)
    except (ValueError, OSError):
        print("usage error: --facts is not readable JSON")
        return 2
    if not isinstance(facts, dict):
        print("usage error: --facts is not a JSON object")
        return 2

    try:
        record = build_record(facts)
    except ProvenanceError as exc:
        print("PROVENANCE: FAIL (%s)" % exc)
        return 1

    raw = canonical_bytes(record)
    if args.out is not None:
        if not os.path.isabs(args.out):
            print("usage error: --out must be an absolute path")
            return 2
        with open(args.out, "wb") as handle:
            handle.write(raw)
    else:
        sys.stdout.buffer.write(raw)
    print("PROVENANCE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
