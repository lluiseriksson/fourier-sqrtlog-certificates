"""Exact-Q and exact-F_q Fourier linear-circuit gate, Morgenstern conservation, and NTT certification."""

from .fourier_certifier import (
    CERT_SCHEMA,
    CertificateVerificationError,
    verify_fourier_certificate_exact,
)
from .fourier_exact import (
    build_hadamard_butterfly_circuit,
    build_hadamard_matrix,
    build_ntt_matrix,
    build_ntt_radix2_circuit,
    eval_circuit_fq,
    eval_circuit_q,
    is_prime_exact,
    is_primitive_root_of_order,
    rat_to_str,
)

__all__ = [
    "CERT_SCHEMA",
    "CertificateVerificationError",
    "verify_fourier_certificate_exact",
    "build_hadamard_butterfly_circuit",
    "build_hadamard_matrix",
    "build_ntt_matrix",
    "build_ntt_radix2_circuit",
    "eval_circuit_fq",
    "eval_circuit_q",
    "is_prime_exact",
    "is_primitive_root_of_order",
    "rat_to_str",
]
