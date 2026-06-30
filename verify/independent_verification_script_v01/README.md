# Project Witness — Independent Verification Script v0.1

## Move

This package is **Move 46 — Build Independent Verification Script**.

It builds an external verifier for the Move 45 full-stack component-version freeze package.

## Target verified by this package

```text
full_stack_component_version_freeze_v01.zip
SHA256: e97e4d6dbd40254439506dea43b02e5cd87623d45ecbd6df153e6cd9568e1333
```

## What this package does

It provides a standalone Python script:

```text
tools/independent_verify_project_witness.py
```

The script verifies the Move 45 package from the outside using only the Python standard library.

## What this package does not do

It does not modify the stack.

It does not repair Project Witness.

It does not perform Move 47.

It does not freeze Local v1 Candidate.

It does not prove truth, verify external reality, prove source trust, sign artifacts, or externally anchor artifacts.
