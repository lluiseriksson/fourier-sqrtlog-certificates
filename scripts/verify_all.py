"""End-to-end Gate-2 verification script for Paper 13.

Checks:
  1. Lean 4 (`lake build` + `AuditAxioms.lean`): 18/18 theorems, 0 warnings, 0 sorry, 0 Classical.choice.
  2. All 16 exact-Q / exact-F_q FOURIER-GATE-CERT-1.0 certificates independently verified (0 floats).
  3. Full pytest suite (including 50/50 live adversarial red-team attacks).
  4. SHA256SUMS.json manifest integrity (or writes manifest with `--write-manifest`).

Author: Lluis Eriksson
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import verify_fourier_certificate_exact

EXPECTED_LEAN_THEOREMS = [
    "FourierSqrtLog.morgenstern_conservation_batched",
    "FourierSqrtLog.coefficient_bitwidth_blowup",
    "FourierSqrtLog.hadamard_butterfly_factor_two",
    "FourierSqrtLog.pythagorean_aspect_identity",
    "FourierSqrtLog.pythagorean_rect_separation_exact",
    "FourierSqrtLog.rect_separation_upper_bound",
    "FourierSqrtLog.rect_separation_lower_bound",
    "FourierSqrtLog.kyber_modulus_ntt_divisibility",
    "FourierSqrtLog.fermat_prime_ntt_roots",
    "FourierSqrtLog.dilithium_modulus_ntt_divisibility",
    "FourierSqrtLog.circulant_three_dft_budget",
    "FourierSqrtLog.toeplitz_circulant_embedding_budget",
    "FourierSqrtLog.batch_non_amortization_linear",
    "FourierSqrtLog.finite_n_crossover_threshold",
    "FourierSqrtLog.complex_vs_ntt_bitwidth_separation",
    "FourierSqrtLog.hadamard_scale_doubling",
    "FourierSqrtLog.rader_prime_reduction_size",
    "FourierSqrtLog.conservation_exclusivity",
]

MANIFEST_SKIP_DIRS = {".git", ".lake", "__pycache__", ".pytest_cache"}
MANIFEST_SKIP_EXTS = {".aux", ".bbl", ".blg", ".log", ".out", ".fls", ".fdb_latexmk", ".synctex.gz", ".pyc"}


def check_lean() -> None:
    lean_dir = ROOT / "lean"
    p1 = subprocess.run(["lake", "build"], cwd=lean_dir, capture_output=True, text=True)
    if p1.returncode != 0:
        raise RuntimeError(f"lake build failed:\n{p1.stdout}\n{p1.stderr}")
    if "warning:" in (p1.stdout + p1.stderr).lower():
        raise RuntimeError(f"Lean warnings detected:\n{p1.stdout}\n{p1.stderr}")
    p2 = subprocess.run(["lake", "env", "lean", "AuditAxioms.lean"], cwd=lean_dir, capture_output=True, text=True)
    if p2.returncode != 0:
        raise RuntimeError(f"AuditAxioms failed:\n{p2.stdout}\n{p2.stderr}")
    out = p2.stdout + p2.stderr
    for banned in ("sorryAx", "Classical.choice", "Lean.ofReduceBool", "Lean.trustCompiler"):
        if banned in out:
            raise RuntimeError(f"Forbidden Lean axiom detected: {banned}")
    for thm in EXPECTED_LEAN_THEOREMS:
        if thm not in out:
            raise RuntimeError(f"Missing Lean theorem in AuditAxioms output: {thm}")
    print(f"[PASS] Lean 4 kernel: {len(EXPECTED_LEAN_THEOREMS)}/18 theorems, 0 warnings, 0 sorry, 0 Classical.choice")


def check_certs() -> None:
    certs = sorted((ROOT / "results" / "certificates").glob("*.cert.json"))
    if len(certs) != 16:
        raise RuntimeError(f"Expected 16 certificates, found {len(certs)}")
    for path in certs:
        data = json.loads(path.read_text(encoding="utf-8"))
        verify_fourier_certificate_exact(data)
    print(f"[PASS] Exact-Q/F_q certificates: {len(certs)}/16 independently verified (0 floats)")


def check_pytest() -> None:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"pytest failed:\n{p.stdout}\n{p.stderr}")
    summary = p.stdout.strip().splitlines()[-1]
    print(f"[PASS] pytest: {summary}")


def _collect_manifest_files() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in MANIFEST_SKIP_DIRS for part in rel.parts):
            continue
        if rel.name == "SHA256SUMS.json" or path.suffix in MANIFEST_SKIP_EXTS:
            continue
        if rel.parts[0] == "paper" and rel.name == "main.pdf":
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[rel.as_posix()] = h
    return hashes


def check_or_write_manifest(write: bool) -> None:
    manifest_path = ROOT / "SHA256SUMS.json"
    current = _collect_manifest_files()
    if write:
        manifest_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[PASS] Wrote SHA256SUMS.json ({len(current)} files)")
        return
    if not manifest_path.exists():
        raise RuntimeError("SHA256SUMS.json missing; run with --write-manifest first.")
    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if recorded != current:
        missing = sorted(set(recorded) - set(current))
        extra = sorted(set(current) - set(recorded))
        changed = sorted(k for k in set(recorded) & set(current) if recorded[k] != current[k])
        raise RuntimeError(f"SHA256SUMS mismatch! missing={missing}, extra={extra}, changed={changed}")
    print(f"[PASS] SHA256SUMS.json: {len(current)}/{len(current)} hashes match")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-manifest", action="store_true")
    args = ap.parse_args()
    check_lean()
    check_certs()
    check_pytest()
    check_or_write_manifest(args.write_manifest)
    print("=== ALL PAPER 13 GATE-2 VERIFICATION CHECKS PASSED ===")


if __name__ == "__main__":
    main()
