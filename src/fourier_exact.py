"""Pure-stdlib exact-Q and exact-F_q finite Fourier transform circuit constructors & evaluators.

Zero floating-point operations anywhere in this module (fractions.Fraction and int mod q only).
Author: Lluis Eriksson
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Sequence, Tuple


def rat_to_str(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def is_prime_exact(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    d = 5
    while d * d <= n:
        if n % d == 0 or n % (d + 2) == 0:
            return False
        d += 6
    return True


def prime_factors_exact(n: int) -> List[int]:
    factors: List[int] = []
    d = 2
    x = n
    while d * d <= x:
        if x % d == 0:
            factors.append(d)
            while x % d == 0:
                x //= d
        d += 1
    if x > 1:
        factors.append(x)
    return factors


def is_primitive_root_of_order(omega: int, N: int, q: int) -> bool:
    if not is_prime_exact(q) or N < 2 or omega <= 0 or omega >= q:
        return False
    if (q - 1) % N != 0:
        return False
    if pow(omega, N, q) != 1:
        return False
    for p in prime_factors_exact(N):
        if pow(omega, N // p, q) == 1:
            return False
    return True


def build_hadamard_matrix(k: int) -> List[List[Fraction]]:
    """Exact recursive 2^k x 2^k Walsh-Hadamard matrix over Q."""
    if k < 1:
        raise ValueError("Require k >= 1.")
    H: List[List[Fraction]] = [[Fraction(1)]]
    for _ in range(k):
        m = len(H)
        new_H: List[List[Fraction]] = [[Fraction(0)] * (2 * m) for _ in range(2 * m)]
        for i in range(m):
            for j in range(m):
                v = H[i][j]
                new_H[i][j] = v
                new_H[i][j + m] = v
                new_H[i + m][j] = v
                new_H[i + m][j + m] = -v
        H = new_H
    return H


def build_hadamard_butterfly_circuit(k: int) -> Tuple[int, List[Dict[str, object]], List[int]]:
    """Construct exact acyclic binary linear circuit for H_{2^k} using L = k * 2^k gates (C = 2)."""
    if k < 1:
        raise ValueError("Require k >= 1.")
    N = 1 << k
    wires = list(range(N))
    gates: List[Dict[str, object]] = []
    next_wire = N
    for stage in range(k):
        step = 1 << stage
        new_wires = [0] * N
        for base in range(0, N, 2 * step):
            for j in range(step):
                u = wires[base + j]
                v = wires[base + j + step]
                # Gate 1: u + v
                gates.append({"in1": u, "in2": v, "a": "1", "b": "1"})
                w_plus = next_wire
                next_wire += 1
                # Gate 2: u - v
                gates.append({"in1": u, "in2": v, "a": "1", "b": "-1"})
                w_minus = next_wire
                next_wire += 1
                new_wires[base + j] = w_plus
                new_wires[base + j + step] = w_minus
        wires = new_wires
    return N, gates, wires


def eval_circuit_q(
    N: int,
    gates: Sequence[Dict[str, object]],
    outputs: Sequence[int],
) -> List[List[Fraction]]:
    """Execute an acyclic binary linear circuit over exact Q on all N basis vectors."""
    M: List[List[Fraction]] = [[Fraction(0)] * N for _ in range(len(outputs))]
    for col in range(N):
        vals: List[Fraction] = [Fraction(1) if i == col else Fraction(0) for i in range(N)]
        for g in gates:
            u = int(g["in1"])
            v = int(g["in2"])
            a = g["a"]
            b = g["b"]
            a_f = a if isinstance(a, Fraction) else Fraction(str(a))
            b_f = b if isinstance(b, Fraction) else Fraction(str(b))
            vals.append(a_f * vals[u] + b_f * vals[v])
        for row, out_w in enumerate(outputs):
            M[row][col] = vals[out_w]
    return M


def build_ntt_matrix(N: int, omega: int, q: int) -> List[List[int]]:
    """Exact N x N Vandermonde NTT matrix F_N[r, c] = omega^(r*c) mod q."""
    return [[pow(omega, (r * c) % N, q) for c in range(N)] for r in range(N)]


def _bit_reverse(x: int, bits: int) -> int:
    out = 0
    for _ in range(bits):
        out = (out << 1) | (x & 1)
        x >>= 1
    return out


def build_ntt_radix2_circuit(
    N: int,
    omega: int,
    q: int,
) -> Tuple[List[Dict[str, int]], List[int]]:
    """Construct exact Cooley-Tukey radix-2 DIT acyclic binary linear circuit for F_N(omega) over F_q."""
    if N < 2 or (N & (N - 1)) != 0:
        raise ValueError("N must be a power of 2 >= 2.")
    if not is_primitive_root_of_order(omega, N, q):
        raise ValueError("omega must be a primitive N-th root of unity mod q.")
    k = N.bit_length() - 1
    # Bit-reversed input wire permutation (free wire routing, 0 gates)
    wires = [_bit_reverse(i, k) for i in range(N)]
    gates: List[Dict[str, int]] = []
    next_wire = N

    for stage in range(1, k + 1):
        m = 1 << stage
        half = m >> 1
        w_m = pow(omega, N // m, q)
        new_wires = [0] * N
        for base in range(0, N, m):
            w = 1
            for j in range(half):
                u = wires[base + j]
                v = wires[base + j + half]
                # Gate 1: u + w * v mod q
                gates.append({"in1": u, "in2": v, "a": 1, "b": w % q})
                w_plus = next_wire
                next_wire += 1
                # Gate 2: u - w * v mod q
                gates.append({"in1": u, "in2": v, "a": 1, "b": (q - (w % q)) % q})
                w_minus = next_wire
                next_wire += 1
                new_wires[base + j] = w_plus
                new_wires[base + j + half] = w_minus
                w = (w * w_m) % q
        wires = new_wires
    return gates, wires


def eval_circuit_fq(
    N: int,
    gates: Sequence[Dict[str, int]],
    outputs: Sequence[int],
    q: int,
) -> List[List[int]]:
    """Execute an acyclic binary linear circuit over F_q on all N basis vectors."""
    M: List[List[int]] = [[0] * N for _ in range(len(outputs))]
    for col in range(N):
        vals = [1 if i == col else 0 for i in range(N)]
        for g in gates:
            u = g["in1"]
            v = g["in2"]
            a = g["a"]
            b = g["b"]
            vals.append((a * vals[u] + b * vals[v]) % q)
        for row, out_w in enumerate(outputs):
            M[row][col] = vals[out_w]
    return M


def circulant_matvec_fq(a: Sequence[int], x: Sequence[int], q: int) -> List[int]:
    """Exact cyclic convolution (C_a x)[r] = sum_c a[(r - c) mod N] * x[c] mod q."""
    N = len(a)
    out = [0] * N
    for r in range(N):
        acc = 0
        for c in range(N):
            acc = (acc + a[(r - c) % N] * x[c]) % q
        out[r] = acc
    return out
