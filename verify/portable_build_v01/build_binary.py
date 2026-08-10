#!/usr/bin/env python3
"""Move 82 build tool.

Invokes the EXPLICITLY SUPPLIED trusted toolchain to build witness-verify
and reports the exact build facts. It never searches PATH, never chooses a
toolchain, and never resolves a default: the adoption gate resolves the
trusted cargo and rustc and passes their absolute paths in.

Builds one profile per invocation. The gate builds `release` (the
preserved portable artefact) and `dev` (used only for behavioural
equivalence testing and never preserved or advertised).

Nothing here modifies the Rust source or the Cargo manifest.
"""

import argparse
import json
import os
import subprocess
import sys


PROFILE_DIR = {"release": "release", "dev": "debug"}
BUILD_TIMEOUT_SECONDS = 3600


class BuildError(Exception):
    """Deterministic, message-only build failure."""


def _require_abs_exec(path, what):
    if not path:
        raise BuildError("%s was not supplied" % what)
    if not os.path.isabs(path):
        raise BuildError("%s must be an absolute path" % what)
    if not os.path.isfile(path):
        raise BuildError("%s is not a regular file" % what)
    if not os.access(path, os.X_OK):
        raise BuildError("%s is not executable" % what)
    return path


def _run(argv, cwd=None, timeout=BUILD_TIMEOUT_SECONDS):
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        raise BuildError("toolchain invocation timed out")
    except OSError:
        # missing, non-executable, or an invalid executable format
        raise BuildError("toolchain invocation could not be launched")
    return proc


def tool_version(tool_path):
    """Exact first line of `<tool> --version`. ANY stderr fails: a
    toolchain that warns while reporting its version is not clean, and
    moving that warning into stdout would launder it."""
    proc = _run([tool_path, "--version"], timeout=120)
    if proc.returncode != 0:
        raise BuildError("could not read version of %s" % tool_path)
    if proc.stderr:
        raise BuildError("%s emitted stderr while reporting its version"
                         % os.path.basename(tool_path))
    text = proc.stdout.decode("utf-8", "replace").strip()
    return text.splitlines()[0] if text else ""


def rustc_host(rustc_path):
    """Host triple as the toolchain itself reports it. Detected, never
    assumed."""
    proc = _run([rustc_path, "-vV"], timeout=120)
    if proc.returncode != 0:
        raise BuildError("could not read rustc host triple")
    if proc.stderr:
        raise BuildError("rustc emitted stderr while reporting -vV")
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("host: "):
            host = line[len("host: "):].strip()
            if not host:
                raise BuildError("rustc reported an empty host triple")
            return host
    raise BuildError("rustc did not report a host triple")


def target_dir_is_absent(manifest_dir):
    return not os.path.exists(os.path.join(manifest_dir, "target"))


def build(cargo, manifest_dir, profile):
    """Build one profile. Returns (binary_path, argv). Fails closed if a
    stale target directory is present, so no previously built artefact can
    ever be mistaken for a fresh one."""
    if profile not in PROFILE_DIR:
        raise BuildError("unsupported profile: %s" % profile)
    if not os.path.isabs(manifest_dir) or not os.path.isdir(manifest_dir):
        raise BuildError("manifest dir must be an absolute directory")

    # Exactly the adopted invocation (`cargo build -q`), plus --release for
    # the release profile. No --locked: the workspace has no dependencies
    # and no committed Cargo.lock, so --locked would fail outright. No
    # --offline either: the honest basis for the offline claim is that the
    # manifest declares zero external crates, which provenance records as a
    # fact, rather than an untested flag the adopted stack has never run.
    argv = [cargo, "build", "-q"]
    if profile == "release":
        argv.append("--release")
    proc = _run(argv, cwd=manifest_dir)
    if proc.returncode != 0:
        raise BuildError("cargo build failed for profile %s" % profile)
    # A warning is not a clean build. Capturing cargo stderr and copying it
    # into stdout while still reporting PASS would launder exactly the
    # evidence the warning-clean contract exists to surface.
    if proc.stderr:
        raise BuildError(
            "cargo build emitted stderr for profile %s (a warning is not a "
            "clean build)" % profile)

    binary = os.path.join(manifest_dir, "target", PROFILE_DIR[profile],
                          "witness-verify")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        raise BuildError("build produced no executable for profile %s"
                         % profile)
    return binary, argv


def main(argv=None):
    parser = argparse.ArgumentParser(description="Move 82 build tool")
    parser.add_argument("--cargo", required=True)
    parser.add_argument("--rustc", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--profile", required=True,
                        choices=sorted(PROFILE_DIR))
    parser.add_argument("--require-clean-target", action="store_true")
    args = parser.parse_args(argv)

    try:
        cargo = _require_abs_exec(args.cargo, "--cargo")
        rustc = _require_abs_exec(args.rustc, "--rustc")
        manifest_dir = args.manifest_dir
        if args.require_clean_target and not target_dir_is_absent(
                manifest_dir):
            raise BuildError(
                "a target directory is already present: refusing to build "
                "so no stale artefact can be reused")
        facts = {
            "cargo_version": tool_version(cargo),
            "rustc_version": tool_version(rustc),
            "rustc_host": rustc_host(rustc),
            "build_profile": args.profile,
        }
        binary, build_argv = build(cargo, manifest_dir, args.profile)
    except BuildError as exc:
        print("BUILD: FAIL (%s)" % exc)
        return 1

    facts["binary_path"] = binary
    facts["build_argv"] = build_argv
    facts["build_stderr_bytes"] = 0
    sys.stdout.write(json.dumps(facts, sort_keys=True,
                                separators=(",", ":"),
                                ensure_ascii=False) + "\n")
    print("BUILD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
