"""Pure-stdlib zero-floating-point-trust certificate verifier (FOURIER-GATE-CERT-1.0).

Supports 4 mutually exclusive modes over exact Q and exact prime fields F_q:
  1. morgenstern_conservation    : Exact Gate-Bit Conservation Law 2 L b >= J N log2(N).
  2. pythagorean_rect_separation : Exact rational Fourier-vs-permutation rectangular price separation.
  3. exact_hadamard_circuit_q    : Independently executes acyclic Q-circuit DAG and verifies H_{2^k}.
  4. exact_ntt_circuit_fq        : Independently executes acyclic F_q-circuit DAG, verifies NTT & circulant.

Author: Lluis Eriksson
"""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any, Dict, List

from .fourier_exact import (
    build_hadamard_matrix,
    build_ntt_matrix,
    circulant_matvec_fq,
    eval_circuit_fq,
    eval_circuit_q,
    is_prime_exact,
    is_primitive_root_of_order,
    rat_to_str,
)

CERT_SCHEMA = "FOURIER-GATE-CERT-1.0"
VALID_MODES = {
    "morgenstern_conservation",
    "pythagorean_rect_separation",
    "exact_hadamard_circuit_q",
    "exact_ntt_circuit_fq",
}

_RAT_RE = re.compile(r"\A-?[0-9]+(?:/[1-9][0-9]*)?\Z")


class CertificateVerificationError(ValueError):
    """Raised whenever an exact certificate fails any mathematical or schema check."""


def _assert_no_floats(obj: Any, path: str = "root") -> None:
    if isinstance(obj, float):
        raise CertificateVerificationError(f"Floating-point value forbidden at {path}: {obj!r}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_floats(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_floats(v, f"{path}[{i}]")


def _parse_int(val: Any, name: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise CertificateVerificationError(f"{name} must be an exact int.")
    return val


def _parse_rat(val: Any, name: str) -> Fraction:
    if isinstance(val, bool):
        raise CertificateVerificationError(f"{name} cannot be bool.")
    if isinstance(val, int):
        return Fraction(val)
    if isinstance(val, str):
        if not _RAT_RE.match(val):
            raise CertificateVerificationError(f"{name} is not a canonical rational string: {val!r}")
        if "/" in val:
            num_s, den_s = val.split("/")
            return Fraction(int(num_s), int(den_s))
        return Fraction(int(val))
    raise CertificateVerificationError(f"{name} must be exact int or rational string.")


def _verify_mode1_morgenstern(cert: Dict[str, Any]) -> Dict[str, Any]:
    J = _parse_int(cert.get("J"), "J")
    k = _parse_int(cert.get("k"), "k")
    if J < 1 or k < 1 or k > 4096:
        raise CertificateVerificationError("Require batch size J >= 1 and 1 <= log2(N) = k <= 4096.")
    N = 1 << k
    if "N" in cert and _parse_int(cert.get("N"), "N") != N:
        raise CertificateVerificationError(f"N must equal 2^k = {N}.")
    L = _parse_rat(cert.get("L"), "L")
    b = _parse_rat(cert.get("b"), "b")
    if L <= 0 or b <= 0:
        raise CertificateVerificationError("Gate count L and bit-width b must be strictly positive.")

    claimed_status = cert.get("claimed_status")
    if claimed_status not in {"feasible", "morgenstern_impossible"}:
        raise CertificateVerificationError("claimed_status must be 'feasible' or 'morgenstern_impossible'.")

    lhs = Fraction(2) * L * b
    rhs = Fraction(J * N * k)
    min_b = Fraction(J * N * k) / (Fraction(2) * L)

    if "min_bitwidth_required" in cert:
        claimed_min_b = _parse_rat(cert.get("min_bitwidth_required"), "min_bitwidth_required")
        if claimed_min_b != min_b:
            raise CertificateVerificationError(f"min_bitwidth_required mismatch: {claimed_min_b} != {min_b}.")

    is_feasible = lhs >= rhs
    if claimed_status == "feasible" and not is_feasible:
        raise CertificateVerificationError(f"Morgenstern conservation violated: 2Lb={lhs} < JNk={rhs}.")
    if claimed_status == "morgenstern_impossible" and is_feasible:
        raise CertificateVerificationError(f"Claimed impossible, but 2Lb={lhs} >= JNk={rhs} is feasible.")

    verdict = "MORGENSTERN_FEASIBLE_CERTIFIED" if is_feasible else "MORGENSTERN_IMPOSSIBLE_CERTIFIED"
    return {
        "schema": CERT_SCHEMA,
        "mode": "morgenstern_conservation",
        "verdict": verdict,
        "J": J,
        "N": N,
        "k": k,
        "L": rat_to_str(L),
        "b": rat_to_str(b),
        "min_bitwidth_required": rat_to_str(min_b),
    }


def _verify_mode2_pythagorean_rect(cert: Dict[str, Any]) -> Dict[str, Any]:
    u = _parse_int(cert.get("u"), "u")
    v = _parse_int(cert.get("v"), "v")
    k = _parse_int(cert.get("k"), "k")
    if not (v > 0 and u > v and k >= 1):
        raise CertificateVerificationError("Require integers u > v > 0 and k >= 1.")

    L = Fraction(2 * u * v, u * u - v * v)
    hyp = Fraction(u * u + v * v, u * u - v * v)
    if Fraction(1) + L * L != hyp * hyp:
        raise CertificateVerificationError("Pythagorean identity 1 + L^2 == hyp^2 failed.")
    delta_rect = hyp - Fraction(1)
    if delta_rect != Fraction(2 * v * v, u * u - v * v):
        raise CertificateVerificationError("Exact rational separation identity failed.")
    # Verify unconditional two-sided algebraic bracket
    lower_b = (L * L) / (Fraction(2) + L)
    upper_b = (L * L) / Fraction(2)
    if not (lower_b < delta_rect < upper_b):
        raise CertificateVerificationError("Two-sided algebraic bracket failed.")

    claimed_L = _parse_rat(cert.get("L"), "L")
    claimed_delta = _parse_rat(cert.get("delta_rect"), "delta_rect")
    claimed_total = _parse_rat(cert.get("total_price_gap"), "total_price_gap")
    if claimed_L != L:
        raise CertificateVerificationError(f"L mismatch: claimed {claimed_L}, exact {L}.")
    if claimed_delta != delta_rect:
        raise CertificateVerificationError(f"delta_rect mismatch: claimed {claimed_delta}, exact {delta_rect}.")
    if claimed_total != delta_rect * Fraction(k):
        raise CertificateVerificationError("total_price_gap mismatch.")

    return {
        "schema": CERT_SCHEMA,
        "mode": "pythagorean_rect_separation",
        "verdict": "PYTHAGOREAN_SEPARATION_CERTIFIED",
        "u": u,
        "v": v,
        "k": k,
        "L": rat_to_str(L),
        "delta_rect": rat_to_str(delta_rect),
        "total_price_gap": rat_to_str(claimed_total),
    }


def _verify_mode3_hadamard_circuit(cert: Dict[str, Any]) -> Dict[str, Any]:
    k = _parse_int(cert.get("k"), "k")
    if k < 1 or k > 6:
        raise CertificateVerificationError("Require 1 <= k <= 6 for exact basis-vector verification.")
    N = 1 << k
    raw_gates = cert.get("gates")
    raw_outputs = cert.get("outputs")
    if not isinstance(raw_gates, list) or not raw_gates:
        raise CertificateVerificationError("gates must be a non-empty list.")
    if not isinstance(raw_outputs, list) or len(raw_outputs) != N:
        raise CertificateVerificationError(f"outputs must have length {N}.")

    parsed_gates: List[Dict[str, object]] = []
    max_weight = Fraction(0)
    for idx, g in enumerate(raw_gates):
        if not isinstance(g, dict):
            raise CertificateVerificationError(f"gates[{idx}] must be a dict.")
        u = _parse_int(g.get("in1"), f"gates[{idx}].in1")
        v = _parse_int(g.get("in2"), f"gates[{idx}].in2")
        max_wire = N + idx
        if not (0 <= u < max_wire and 0 <= v < max_wire):
            raise CertificateVerificationError(f"gates[{idx}] wire index out of acyclic range [0, {max_wire}).")
        a = _parse_rat(g.get("a"), f"gates[{idx}].a")
        b = _parse_rat(g.get("b"), f"gates[{idx}].b")
        w = abs(a) + abs(b)
        if w > max_weight:
            max_weight = w
        parsed_gates.append({"in1": u, "in2": v, "a": a, "b": b})

    total_wires = N + len(parsed_gates)
    outputs = [_parse_int(x, f"outputs[{i}]") for i, x in enumerate(raw_outputs)]
    if any(not (0 <= w < total_wires) for w in outputs):
        raise CertificateVerificationError("Output wire index out of range.")

    M = eval_circuit_q(N, parsed_gates, outputs)
    H = build_hadamard_matrix(k)
    if M != H:
        raise CertificateVerificationError("Executed circuit matrix does not match exact Walsh-Hadamard H_{2^k}.")

    # Independently check orthogonality M^T M == N I_N
    for i in range(N):
        for j in range(N):
            dot = sum((M[r][i] * M[r][j] for r in range(N)), Fraction(0))
            expected = Fraction(N) if i == j else Fraction(0)
            if dot != expected:
                raise CertificateVerificationError("Orthogonality M^T M == N I_N failed.")

    L = len(parsed_gates)
    if "claimed_gate_count" in cert and _parse_int(cert.get("claimed_gate_count"), "claimed_gate_count") != L:
        raise CertificateVerificationError("claimed_gate_count mismatch.")
    if "claimed_max_weight" in cert and _parse_rat(cert.get("claimed_max_weight"), "claimed_max_weight") != max_weight:
        raise CertificateVerificationError("claimed_max_weight mismatch.")

    # Verify integer bit-width bound if max_weight <= 2^b_int
    b_int = 1
    while Fraction(1 << b_int) < max_weight:
        b_int += 1
    if 2 * L * b_int < N * k:
        raise CertificateVerificationError("Impossible Morgenstern violation inside exact Hadamard circuit.")

    return {
        "schema": CERT_SCHEMA,
        "mode": "exact_hadamard_circuit_q",
        "verdict": "HADAMARD_CIRCUIT_CERTIFIED",
        "k": k,
        "N": N,
        "gate_count": L,
        "max_weight": rat_to_str(max_weight),
        "morgenstern_ratio": rat_to_str(Fraction(2 * L * b_int, N * k)),
    }


def _verify_mode4_ntt_circuit(cert: Dict[str, Any]) -> Dict[str, Any]:
    q = _parse_int(cert.get("q"), "q")
    N = _parse_int(cert.get("N"), "N")
    omega = _parse_int(cert.get("omega"), "omega")
    if not is_prime_exact(q):
        raise CertificateVerificationError(f"Modulus q={q} is not prime.")
    if N < 2 or N > 64 or (N & (N - 1)) != 0:
        raise CertificateVerificationError("Require power-of-two N in [2, 64].")
    if not is_primitive_root_of_order(omega, N, q):
        raise CertificateVerificationError(f"omega={omega} is not a primitive {N}-th root of unity mod {q}.")

    raw_gates = cert.get("gates")
    raw_outputs = cert.get("outputs")
    if not isinstance(raw_gates, list) or not raw_gates:
        raise CertificateVerificationError("gates must be a non-empty list.")
    if not isinstance(raw_outputs, list) or len(raw_outputs) != N:
        raise CertificateVerificationError(f"outputs must have length {N}.")

    parsed_gates: List[Dict[str, int]] = []
    for idx, g in enumerate(raw_gates):
        if not isinstance(g, dict):
            raise CertificateVerificationError(f"gates[{idx}] must be a dict.")
        u = _parse_int(g.get("in1"), f"gates[{idx}].in1")
        v = _parse_int(g.get("in2"), f"gates[{idx}].in2")
        max_wire = N + idx
        if not (0 <= u < max_wire and 0 <= v < max_wire):
            raise CertificateVerificationError(f"gates[{idx}] wire index out of acyclic range [0, {max_wire}).")
        a = _parse_int(g.get("a"), f"gates[{idx}].a")
        b = _parse_int(g.get("b"), f"gates[{idx}].b")
        if not (0 <= a < q and 0 <= b < q):
            raise CertificateVerificationError(f"gates[{idx}] coefficients must be canonical residues in [0, {q}).")
        parsed_gates.append({"in1": u, "in2": v, "a": a, "b": b})

    total_wires = N + len(parsed_gates)
    outputs = [_parse_int(x, f"outputs[{i}]") for i, x in enumerate(raw_outputs)]
    if any(not (0 <= w < total_wires) for w in outputs):
        raise CertificateVerificationError("Output wire index out of range.")

    M = eval_circuit_fq(N, parsed_gates, outputs, q)
    F = build_ntt_matrix(N, omega, q)
    if M != F:
        raise CertificateVerificationError("Executed F_q circuit matrix does not match exact NTT F_N(omega).")

    L = len(parsed_gates)
    if "claimed_gate_count" in cert and _parse_int(cert.get("claimed_gate_count"), "claimed_gate_count") != L:
        raise CertificateVerificationError("claimed_gate_count mismatch.")

    circulant_verified = False
    if "circulant_check" in cert and cert["circulant_check"] is not None:
        cc = cert["circulant_check"]
        if not isinstance(cc, dict):
            raise CertificateVerificationError("circulant_check must be a dict.")
        raw_a = cc.get("a")
        raw_x = cc.get("x")
        raw_y = cc.get("y")
        if not (isinstance(raw_a, list) and isinstance(raw_x, list) and isinstance(raw_y, list)):
            raise CertificateVerificationError("circulant_check fields a, x, y must all be lists.")
        a_vec = [_parse_int(x, "a") for x in raw_a]
        x_vec = [_parse_int(x, "x") for x in raw_x]
        y_claimed = [_parse_int(x, "y") for x in raw_y]
        if len(a_vec) != N or len(x_vec) != N or len(y_claimed) != N:
            raise CertificateVerificationError("circulant_check vectors must have length N.")
        if any(not (0 <= v < q) for v in a_vec + x_vec + y_claimed):
            raise CertificateVerificationError("circulant_check entries must lie in [0, q).")
        # Compute via verified NTT matrix M: y = F^{-1}((M a) * (M x))
        Ma = [sum(M[r][c] * a_vec[c] for c in range(N)) % q for r in range(N)]
        Mx = [sum(M[r][c] * x_vec[c] for c in range(N)) % q for r in range(N)]
        prod = [(Ma[r] * Mx[r]) % q for r in range(N)]
        omega_inv = pow(omega, q - 2, q)
        N_inv = pow(N, q - 2, q)
        F_inv = build_ntt_matrix(N, omega_inv, q)
        y_ntt = [(N_inv * sum(F_inv[r][c] * prod[c] for c in range(N))) % q for r in range(N)]
        y_direct = circulant_matvec_fq(a_vec, x_vec, q)
        if y_ntt != y_direct or y_claimed != y_direct:
            raise CertificateVerificationError("Circulant convolution theorem verification failed.")
        circulant_verified = True

    return {
        "schema": CERT_SCHEMA,
        "mode": "exact_ntt_circuit_fq",
        "verdict": "NTT_CIRCUIT_CERTIFIED",
        "q": q,
        "N": N,
        "omega": omega,
        "gate_count": L,
        "field_bits": q.bit_length(),
        "circulant_verified": circulant_verified,
    }


def verify_fourier_certificate_exact(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a FOURIER-GATE-CERT-1.0 JSON dictionary using exact Q / F_q arithmetic only."""
    if not isinstance(cert, dict):
        raise CertificateVerificationError("Certificate must be a JSON object.")
    _assert_no_floats(cert)
    if cert.get("schema") != CERT_SCHEMA:
        raise CertificateVerificationError(f"Unsupported schema: {cert.get('schema')!r}")
    mode = cert.get("mode")
    if mode not in VALID_MODES:
        raise CertificateVerificationError(f"Unknown mode: {mode!r}")

    if mode == "morgenstern_conservation":
        return _verify_mode1_morgenstern(cert)
    if mode == "pythagorean_rect_separation":
        return _verify_mode2_pythagorean_rect(cert)
    if mode == "exact_hadamard_circuit_q":
        return _verify_mode3_hadamard_circuit(cert)
    return _verify_mode4_ntt_circuit(cert)
