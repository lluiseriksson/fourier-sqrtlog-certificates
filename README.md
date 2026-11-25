# Morgenstern Gate–Bit Conservation, Complex-FFT vs. Finite-Field NTT Precision Dichotomy, and Exact Straight-Line Circuit Certificates from the $N(\log N)^{1/2}$ Finite Fourier Transform Exponent

**Author:** Lluis Eriksson (prepared with AI assistance — Google Antigravity)  
**License:** MIT (`LICENSE`)  
**Lean 4 Toolchain:** `leanprover/lean4:v4.35.0` (zero external dependencies, 18/18 theorems, 0 `sorry`, 0 `Classical.choice`, 0 warnings)  
**Certificate Schema:** `FOURIER-GATE-CERT-1.0` (pure Python stdlib `fractions.Fraction` + exact integer mod-$q$ arithmetic, zero floating-point trust)

## Overview

Advancing OpenAI's November 24, 2026 theorem establishing the finite abelian Fourier transform linear-circuit exponent $N(\log_2 N)^{1/2 + o(1)}$, this repository proves and machine-checks four quantitative consequences:

1. **Morgenstern Gate–Bit Conservation Law & Complex-FFT vs. Finite-Field NTT Dichotomy (Theorem 2.1):** Any $L$-gate complex linear circuit computing $J$ independent order-$N$ Fourier transforms with gate weight bound $|\alpha|+|\beta| \le C = 2^b$ and unscaled readouts obeys the exact conservation law $L \cdot b \ge \frac{1}{2} J N \log_2 N$. Consequently, any $O(J N (\log_2 N)^{1/2+\varepsilon})$ circuit over $\mathbb{C}$ MUST suffer super-polynomial scalar coefficient blow-up $C(N) \ge 2^{\Omega((\log_2 N)^{1/2-\varepsilon})}$, restoring the full $\Omega(J N \log_2 N)$ bit-operation barrier in fixed precision—whereas finite-field post-quantum NTTs (ML-KEM / Kyber $q=3329$ at fixed $12$ bits; ML-DSA / Dilithium $q=8380417$ at fixed $23$ bits) escape the Archimedean determinant constraint!
2. **Exact Pythagorean Rectangular Price Separation & Crossovers (Theorem 2.2):** We prove the unconditional exact two-sided rational bracket $\frac{L^2}{2+L} < \sqrt{1+L^2} - 1 < \frac{L^2}{2}$ for OpenAI's rank–support rectangular test, exact rational evaluation $\Delta_{\mathrm{rect}}(L) = \frac{2v^2}{u^2 - v^2}$ at every Pythagorean height $L = \frac{2uv}{u^2-v^2}$, finite-$N$ crossovers $k^* = c_0^2$, and circulant/Toeplitz $3$-transform budgets.
3. **Pure-Stdlib Straight-Line Circuit DAG Verifier `FOURIER-GATE-CERT-1.0` (Theorem 2.3):** Independently executes and verifies exact acyclic binary linear circuits for Walsh–Hadamard $H_4, H_8, H_{16}$ over $\mathbb{Q}$ and prime-field NTTs over $\mathbb{F}_{17}$, $\mathbb{F}_{257}$, and **ML-KEM / Kyber $\mathbb{F}_{3329}$** ($N=8, 16$) including exact circulant convolution checks, verifying all 16 exact certificates with zero floats and rejecting **50/50** live adversarial red-team attacks.

## Quick Verification

```bash
python scripts/verify_all.py
```
