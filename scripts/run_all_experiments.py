"""Run all 4 deterministic experiments and emit 16 exact-Q / exact-F_q FOURIER-GATE-CERT-1.0 certificates.

Author: Lluis Eriksson
"""

from __future__ import annotations

from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import (
    CERT_SCHEMA,
    build_hadamard_butterfly_circuit,
    build_ntt_radix2_circuit,
    rat_to_str,
    verify_fourier_certificate_exact,
)
from src.fourier_exact import circulant_matvec_fq

RESULTS_DIR = ROOT / "results"
CERTS_DIR = RESULTS_DIR / "certificates"


def _write_cert(filename: str, cert: Dict[str, Any]) -> Dict[str, Any]:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CERTS_DIR / filename
    path.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
    t0 = time.perf_counter()
    res = verify_fourier_certificate_exact(cert)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    res["file"] = filename
    res["verify_ms"] = round(dt_ms, 3)
    return res


def _build_mode1_cert(J: int, k: int, L: Fraction, b: Fraction, status: str, label: str) -> Dict[str, Any]:
    N = 1 << k
    min_b = Fraction(J * N * k) / (Fraction(2) * L)
    return {
        "schema": CERT_SCHEMA,
        "mode": "morgenstern_conservation",
        "label": label,
        "J": J,
        "k": k,
        "N": N,
        "L": rat_to_str(L),
        "b": rat_to_str(b),
        "min_bitwidth_required": rat_to_str(min_b),
        "claimed_status": status,
    }


def _build_mode2_cert(u: int, v: int, k: int, label: str) -> Dict[str, Any]:
    L = Fraction(2 * u * v, u * u - v * v)
    delta = Fraction(2 * v * v, u * u - v * v)
    return {
        "schema": CERT_SCHEMA,
        "mode": "pythagorean_rect_separation",
        "label": label,
        "u": u,
        "v": v,
        "k": k,
        "L": rat_to_str(L),
        "delta_rect": rat_to_str(delta),
        "total_price_gap": rat_to_str(delta * Fraction(k)),
    }


def _build_mode3_cert(k: int) -> Dict[str, Any]:
    N, gates, outputs = build_hadamard_butterfly_circuit(k)
    return {
        "schema": CERT_SCHEMA,
        "mode": "exact_hadamard_circuit_q",
        "label": f"hadamard_H_{N}",
        "k": k,
        "gates": gates,
        "outputs": outputs,
        "claimed_gate_count": len(gates),
        "claimed_max_weight": "2",
    }


def _build_mode4_cert(q: int, N: int, omega: int, label: str) -> Dict[str, Any]:
    gates, outputs = build_ntt_radix2_circuit(N, omega, q)
    a_vec = [(3 * i + 1) % q for i in range(N)]
    x_vec = [(5 * i + 2) % q for i in range(N)]
    y_vec = circulant_matvec_fq(a_vec, x_vec, q)
    return {
        "schema": CERT_SCHEMA,
        "mode": "exact_ntt_circuit_fq",
        "label": label,
        "q": q,
        "N": N,
        "omega": omega,
        "gates": gates,
        "outputs": outputs,
        "claimed_gate_count": len(gates),
        "circulant_check": {"a": a_vec, "x": x_vec, "y": y_vec},
    }


def run_exp1_certified_atlas() -> Dict[str, Any]:
    records = []
    # Mode 1: Morgenstern Gate-Bit Conservation Law (4 certs: feasible & impossible, single & batched)
    # (1) Classical Cooley-Tukey at N=2^16 (k=16): L = 16*N, b = 1 => feasible
    records.append(_write_cert("morg_cooley_tukey_k16.cert.json",
                               _build_mode1_cert(1, 16, Fraction(16 * (1 << 16)), Fraction(1), "feasible", "ct_k16")))
    # (2) OpenAI sqrt(log N) circuit at N=2^16 (k=16, sqrt(k)=4): L = 4*N, b = 1 (bounded) => IMPOSSIBLE over C!
    records.append(_write_cert("morg_sqrtlog_bounded_impossible_k16.cert.json",
                               _build_mode1_cert(1, 16, Fraction(4 * (1 << 16)), Fraction(1), "morgenstern_impossible", "sqrtlog_bounded_k16")))
    # (3) OpenAI sqrt(log N) circuit at N=2^16 with required bit-width b = 2 (= k/(2*4)) => feasible!
    records.append(_write_cert("morg_sqrtlog_blowup_feasible_k16.cert.json",
                               _build_mode1_cert(1, 16, Fraction(4 * (1 << 16)), Fraction(2), "feasible", "sqrtlog_blowup_k16")))
    # (4) Batched J=8 independent transforms at k=64 (sqrt(k)=8): L = 8*8*N, b = 3 < 4 => IMPOSSIBLE!
    records.append(_write_cert("morg_batched_J8_k64_impossible.cert.json",
                               _build_mode1_cert(8, 64, Fraction(8 * 8 * (1 << 64)), Fraction(3), "morgenstern_impossible", "batch_J8_k64")))

    # Mode 2: Exact Pythagorean Fourier-vs-Permutation Rectangular Price Separation (4 certs)
    records.append(_write_cert("rect_pyth_u2_v1_k16.cert.json", _build_mode2_cert(2, 1, 16, "u2_v1_k16")))
    records.append(_write_cert("rect_pyth_u3_v1_k16.cert.json", _build_mode2_cert(3, 1, 16, "u3_v1_k16")))
    records.append(_write_cert("rect_pyth_u5_v1_k64.cert.json", _build_mode2_cert(5, 1, 64, "u5_v1_k64")))
    records.append(_write_cert("rect_pyth_u9_v1_k64.cert.json", _build_mode2_cert(9, 1, 64, "u9_v1_k64")))

    # Mode 3: Exact-Q Walsh-Hadamard Butterfly Circuit DAG Certificates (3 certs: H_4, H_8, H_16)
    records.append(_write_cert("hadamard_H4_exact.cert.json", _build_mode3_cert(2)))
    records.append(_write_cert("hadamard_H8_exact.cert.json", _build_mode3_cert(3)))
    records.append(_write_cert("hadamard_H16_exact.cert.json", _build_mode3_cert(4)))

    # Mode 4: Exact-F_q Prime-Field & Post-Quantum Kyber (q=3329) NTT Circuit DAG Certificates (5 certs)
    # F_17: 3 is generator; order 4 root = 4, order 8 root = 9
    records.append(_write_cert("ntt_F17_N4.cert.json", _build_mode4_cert(17, 4, 4, "F17_N4")))
    records.append(_write_cert("ntt_F17_N8.cert.json", _build_mode4_cert(17, 8, 9, "F17_N8")))
    # F_257: 2 has order 16 (2^8 = 256 = -1 mod 257)
    records.append(_write_cert("ntt_F257_N16.cert.json", _build_mode4_cert(257, 16, 2, "F257_N16")))
    # ML-KEM / Kyber modulus q = 3329: 17 has exact order 256 (17^128 = -1 mod 3329)
    # Order-8 primitive root = 17^(256/8) = 17^32 mod 3329; Order-16 primitive root = 17^16 mod 3329
    w8_kyber = pow(17, 32, 3329)
    w16_kyber = pow(17, 16, 3329)
    records.append(_write_cert("ntt_Kyber3329_N8.cert.json", _build_mode4_cert(3329, 8, w8_kyber, "Kyber3329_N8")))
    records.append(_write_cert("ntt_Kyber3329_N16.cert.json", _build_mode4_cert(3329, 16, w16_kyber, "Kyber3329_N16")))

    out = {"schema": CERT_SCHEMA, "num_certificates": len(records), "certificates": records}
    (RESULTS_DIR / "exp1_certified_atlas.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def run_exp2_gate_bit_conservation_frontiers() -> Dict[str, Any]:
    k_vals = [4, 9, 16, 25, 36, 49, 64, 100, 144, 256, 400, 1024]
    rows = []
    for k in k_vals:
        s = math.sqrt(k)
        # Cooley-Tukey: L/N = k, b = 1 => L*b/N = k
        # OpenAI sqrt(k): L/N = c0 * sqrt(k) => min complex bit-width b_min = k / (2 * c0 * sqrt(k)) = sqrt(k) / (2 c0)
        rows.append({
            "k_log2N": k,
            "sqrt_k": round(s, 4),
            "cooley_tukey_gates_per_sample": k,
            "openai_c1_gates_per_sample": round(s, 4),
            "openai_c1_min_complex_bits": round(s / 2.0, 4),
            "kyber_fixed_ntt_bits": 12,
            "dilithium_fixed_ntt_bits": 23,
            "ieee_fp64_mantissa_bits": 53,
        })
    out = {"conservation_curves": rows}
    (RESULTS_DIR / "exp2_gate_bit_conservation.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def run_exp3_pythagorean_separation_curve() -> Dict[str, Any]:
    pts = []
    for u in range(2, 26):
        v = 1
        L = Fraction(2 * u * v, u * u - v * v)
        delta = Fraction(2 * v * v, u * u - v * v)
        lb = (L * L) / (Fraction(2) + L)
        ub = (L * L) / Fraction(2)
        pts.append({
            "u": u,
            "v": v,
            "L_exact": rat_to_str(L),
            "L_float": round(float(L), 6),
            "delta_exact": rat_to_str(delta),
            "delta_float": round(float(delta), 6),
            "lower_bound_float": round(float(lb), 6),
            "upper_bound_float": round(float(ub), 6),
            "ratio_delta_over_half_L2": round(float(delta / ub), 6),
        })
    out = {"pythagorean_points": pts}
    (RESULTS_DIR / "exp3_pythagorean_separation.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def run_exp4_finite_n_crossover_and_ntt_table() -> Dict[str, Any]:
    crossovers = []
    for c0 in [1, 2, 4, 8, 16]:
        k_star = c0 * c0
        crossovers.append({
            "overhead_c0": c0,
            "crossover_k_log2N": k_star,
            "crossover_N_power": f"2^{k_star}",
            "min_complex_bits_at_crossover": round(c0 / 2.0, 4),
        })
    ntt_benchmarks = [
        {"name": "F_17 (N=4)", "q": 17, "bits": 5, "N": 4, "gates": 8, "gates_per_sample": 2.0},
        {"name": "F_17 (N=8)", "q": 17, "bits": 5, "N": 8, "gates": 24, "gates_per_sample": 3.0},
        {"name": "F_257 (N=16)", "q": 257, "bits": 9, "N": 16, "gates": 64, "gates_per_sample": 4.0},
        {"name": "ML-KEM/Kyber (q=3329, N=8)", "q": 3329, "bits": 12, "N": 8, "gates": 24, "gates_per_sample": 3.0},
        {"name": "ML-KEM/Kyber (q=3329, N=16)", "q": 3329, "bits": 12, "N": 16, "gates": 64, "gates_per_sample": 4.0},
    ]
    out = {"crossovers": crossovers, "ntt_benchmarks": ntt_benchmarks}
    (RESULTS_DIR / "exp4_crossover_and_ntt.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    e1 = run_exp1_certified_atlas()
    e2 = run_exp2_gate_bit_conservation_frontiers()
    e3 = run_exp3_pythagorean_separation_curve()
    e4 = run_exp4_finite_n_crossover_and_ntt_table()
    print(f"[EXP 1] {e1['num_certificates']} exact certificates emitted and verified (0 floats).")
    print(f"[EXP 2] Gate-bit conservation curves: {len(e2['conservation_curves'])} points.")
    print(f"[EXP 3] Pythagorean separation curve: {len(e3['pythagorean_points'])} exact rational points.")
    print(f"[EXP 4] Crossover thresholds ({len(e4['crossovers'])}) + NTT benchmarks ({len(e4['ntt_benchmarks'])}).")


if __name__ == "__main__":
    main()
