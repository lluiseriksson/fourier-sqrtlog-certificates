"""Comprehensive pytest + 50 live adversarial red-team attack suite for Paper 13.

Author: Lluis Eriksson
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import (
    CERT_SCHEMA,
    CertificateVerificationError,
    is_prime_exact,
    is_primitive_root_of_order,
    verify_fourier_certificate_exact,
)

CERTS_DIR = ROOT / "results" / "certificates"


def _load(name: str) -> dict:
    return json.loads((CERTS_DIR / name).read_text(encoding="utf-8"))


def test_all_16_emitted_certificates_verify_cleanly() -> None:
    cert_files = sorted(CERTS_DIR.glob("*.cert.json"))
    assert len(cert_files) == 16
    for path in cert_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        res = verify_fourier_certificate_exact(data)
        assert res["schema"] == CERT_SCHEMA
        assert "CERTIFIED" in res["verdict"]


def test_prime_and_primitive_root_exact_checks() -> None:
    assert is_prime_exact(17) and is_prime_exact(257) and is_prime_exact(3329) and is_prime_exact(8380417)
    assert not is_prime_exact(15) and not is_prime_exact(1)
    assert is_primitive_root_of_order(pow(17, 16, 3329), 16, 3329)
    assert not is_primitive_root_of_order(1, 16, 3329)
    assert not is_primitive_root_of_order(pow(17, 32, 3329), 16, 3329)


def test_50_adversarial_red_team_attacks_rejected() -> None:
    c_morg_ok = _load("morg_cooley_tukey_k16.cert.json")
    c_morg_imp = _load("morg_sqrtlog_bounded_impossible_k16.cert.json")
    c_pyth = _load("rect_pyth_u3_v1_k16.cert.json")
    c_had = _load("hadamard_H8_exact.cert.json")
    c_ntt = _load("ntt_Kyber3329_N8.cert.json")

    attacks: list[tuple[str, dict]] = []

    def add(name: str, base: dict, mutator) -> None:
        c = copy.deepcopy(base)
        mutator(c)
        attacks.append((name, c))

    # --- Schema & Zero-Float Enforcement (A01-A09) ---
    add("A01_wrong_schema", c_morg_ok, lambda c: c.__setitem__("schema", "FAKE-1.0"))
    add("A02_unknown_mode", c_morg_ok, lambda c: c.__setitem__("mode", "bogus"))
    add("A03_float_b", c_morg_ok, lambda c: c.__setitem__("b", 1.0))
    add("A04_float_gate_coeff", c_had, lambda c: c["gates"][0].__setitem__("a", 1.0))
    add("A05_decimal_string", c_pyth, lambda c: c.__setitem__("L", "0.75"))
    add("A06_sci_notation", c_pyth, lambda c: c.__setitem__("delta_rect", "2.5e-1"))
    add("A07_zero_denom", c_morg_ok, lambda c: c.__setitem__("b", "1/0"))
    add("A08_bool_as_int_k", c_morg_ok, lambda c: c.__setitem__("k", True))
    add("A09_trailing_newline_rat", c_morg_ok, lambda c: c.__setitem__("b", "1\n"))

    # --- Mode 1: Morgenstern Conservation Attacks (A10-A18) ---
    add("A10_claim_impossible_is_feasible", c_morg_imp, lambda c: c.__setitem__("claimed_status", "feasible"))
    add("A11_claim_feasible_is_impossible", c_morg_ok, lambda c: c.__setitem__("claimed_status", "morgenstern_impossible"))
    add("A12_wrong_N_power", c_morg_ok, lambda c: c.__setitem__("N", 12345))
    add("A13_zero_J", c_morg_ok, lambda c: c.__setitem__("J", 0))
    add("A14_zero_L", c_morg_ok, lambda c: c.__setitem__("L", "0"))
    add("A15_negative_b", c_morg_ok, lambda c: c.__setitem__("b", "-1"))
    add("A16_tamper_min_bitwidth", c_morg_ok, lambda c: c.__setitem__("min_bitwidth_required", "1/99"))
    add("A17_invalid_status_str", c_morg_ok, lambda c: c.__setitem__("claimed_status", "maybe"))
    add("A18_zero_k", c_morg_ok, lambda c: c.__setitem__("k", 0))

    # --- Mode 2: Pythagorean Rectangular Separation Attacks (A19-A26) ---
    add("A19_u_eq_v", c_pyth, lambda c: c.update({"u": 3, "v": 3}))
    add("A20_u_lt_v", c_pyth, lambda c: c.update({"u": 2, "v": 3}))
    add("A21_v_zero", c_pyth, lambda c: c.__setitem__("v", 0))
    add("A22_tamper_L", c_pyth, lambda c: c.__setitem__("L", "1"))
    add("A23_tamper_delta_rect", c_pyth, lambda c: c.__setitem__("delta_rect", "1/2"))
    add("A24_tamper_total_gap", c_pyth, lambda c: c.__setitem__("total_price_gap", "99"))
    add("A25_k_zero_rect", c_pyth, lambda c: c.__setitem__("k", 0))
    add("A26_bool_u", c_pyth, lambda c: c.__setitem__("u", True))

    # --- Mode 3: Exact-Q Hadamard Circuit DAG Attacks (A27-A36) ---
    add("A27_cyclic_self_wire", c_had, lambda c: c["gates"][0].__setitem__("in1", 8))
    add("A28_future_wire_ref", c_had, lambda c: c["gates"][0].__setitem__("in2", 12))
    add("A29_negative_wire_ref", c_had, lambda c: c["gates"][0].__setitem__("in1", -1))
    add("A30_tamper_gate_sign", c_had, lambda c: c["gates"][1].__setitem__("b", "1"))
    add("A31_swap_two_outputs", c_had, lambda c: c["outputs"].__setitem__(0, c["outputs"][1]))
    add("A32_wrong_output_len", c_had, lambda c: c["outputs"].pop())
    add("A33_out_of_range_output", c_had, lambda c: c["outputs"].__setitem__(0, 999))
    add("A34_lie_gate_count", c_had, lambda c: c.__setitem__("claimed_gate_count", 10))
    add("A35_lie_max_weight", c_had, lambda c: c.__setitem__("claimed_max_weight", "1"))
    add("A36_empty_gates", c_had, lambda c: c.__setitem__("gates", []))

    # --- Mode 4: Exact-F_q NTT & Circulant Circuit DAG Attacks (A37-A50) ---
    add("A37_composite_modulus", c_ntt, lambda c: c.__setitem__("q", 3327))
    add("A38_non_primitive_root_1", c_ntt, lambda c: c.__setitem__("omega", 1))
    add("A39_half_order_root", c_ntt, lambda c: c.__setitem__("omega", pow(c["omega"], 2, c["q"])))
    add("A40_non_pow2_N", c_ntt, lambda c: c.__setitem__("N", 6))
    add("A41_ntt_cyclic_wire", c_ntt, lambda c: c["gates"][0].__setitem__("in1", 8))
    add("A42_ntt_noncanonical_coeff", c_ntt, lambda c: c["gates"][0].__setitem__("a", 3330))
    add("A43_ntt_neg_coeff", c_ntt, lambda c: c["gates"][0].__setitem__("b", -1))
    add("A44_ntt_tamper_twiddle", c_ntt, lambda c: c["gates"][-1].__setitem__("b", 1))
    add("A45_ntt_lie_gate_count", c_ntt, lambda c: c.__setitem__("claimed_gate_count", 12))
    add("A46_circulant_tamper_y", c_ntt, lambda c: c["circulant_check"]["y"].__setitem__(0, (c["circulant_check"]["y"][0] + 1) % 3329))
    add("A47_circulant_bad_len", c_ntt, lambda c: c["circulant_check"]["a"].pop())
    add("A48_circulant_out_of_range_val", c_ntt, lambda c: c["circulant_check"]["x"].__setitem__(0, 3329))
    add("A49_circulant_non_list_a", c_ntt, lambda c: c["circulant_check"].__setitem__("a", 123))
    add("A50_morg_huge_k_dos", c_morg_ok, lambda c: c.__setitem__("k", 1000000))

    assert len(attacks) == 50
    for name, bad_cert in attacks:
        with pytest.raises(CertificateVerificationError, match="."):
            verify_fourier_certificate_exact(bad_cert)
