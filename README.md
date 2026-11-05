# RUAX-CAI Loan Amortization Capsule

```text
Michael Aaron Russell
ORCID: 0009-0001-3360-6709
An enterprise-grade deterministic loan amortization verification capsule utilizing $10^{18}$ WAD fixed-point integer arithmetic, exact-rational oracle validation, and automated AST-level mutation testing for zero-drift financial computing.

## Core Features

* **Zero-Drift WAD18 Engine**: Replaces non-deterministic floating-point math with fixed-point integer scaling ($W = 10^{18}$), ensuring bit-exact reproducibility across heterogeneous hardware and platforms.
* **Exact-Rational Oracle Validation**: Benchmarks financial schedules against high-precision rational fraction models (`fractions.Fraction`).
* **Automated AST Mutation Testing**: Programmatically walks the Abstract Syntax Tree of `amort.py`, injecting operator swaps and constant perturbations to measure test suite efficacy and ensure complete mutant elimination.
* **Cryptographic Integrity Hashing**: Chains execution vectors and outputs into an immutable SHA-256 root hash (`RUAX-WAD18-AMORT-v1`) to detect silent regressions or environment drift.

## File Structure

* `amort.py` — Core WAD18 loan amortization engine and parser.
* `capsule.py` — Verification runner, invariant auditor, and AST mutation engine.
* `GOLDEN.json` — Immutable cryptographic root baseline.
* `MANIFEST.sha256` — Cryptographic file manifest for source integrity.

## Usage & Verification

1. **Initialize Golden Baseline & Manifest:**
   ```bash
   python3 capsule.py --init
