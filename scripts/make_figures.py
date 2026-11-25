"""Generate 3 publication-grade 300-DPI figures for Paper 13.

Author: Lluis Eriksson
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGDIR = ROOT / "paper" / "figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 10.5,
    "axes.labelsize": 10,
    "legend.fontsize": 8.0,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.28,
})


def make_fig1() -> None:
    d = json.loads((RESULTS / "exp2_gate_bit_conservation.json").read_text(encoding="utf-8"))
    rows = d["conservation_curves"]
    ks = [r["k_log2N"] for r in rows]
    ct = [r["cooley_tukey_gates_per_sample"] for r in rows]
    oai = [r["openai_c1_gates_per_sample"] for r in rows]
    b_min = [r["openai_c1_min_complex_bits"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.2), constrained_layout=True)

    # Panel (a): Gate count per sample vs log2(N)
    ax1.loglog(ks, ct, "o-", color="#7f7f7f", lw=2.0, ms=4.5, label=r"Cooley--Tukey FFT ($L/N = \log_2 N$)")
    ax1.loglog(ks, oai, "s-", color="#1565c0", lw=2.2, ms=5.0, label=r"OpenAI Nov 2026 ($L/N = \sqrt{\log_2 N}$)")
    ax1.loglog(ks, [0.5 * k for k in ks], "--", color="#c62828", lw=1.4, label=r"Morgenstern bounded-coeff ($C=2$): $\frac{1}{2}\log_2 N$")
    ax1.fill_between(ks, oai, [0.5 * k for k in ks], where=[o < 0.5 * k for o, k in zip(oai, ks)],
                     color="#ffebee", alpha=0.55, label=r"Forbidden for bounded $C=2$ over $\mathbb{C}$")
    ax1.set_xlabel(r"Transform scale $k = \log_2 N$")
    ax1.set_ylabel(r"Binary linear gates per sample $L / N$")
    ax1.set_title("(a) Linear Gate Scaling vs. Bounded-Weight Barrier")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=7.6)

    # Panel (b): Complex FFT coefficient bit-width blow-up vs fixed-modulus Post-Quantum NTT
    ax2.semilogx(ks, b_min, "s-", color="#c62828", lw=2.2, ms=5.0,
                 label=r"Complex FFT min coeff bits $b_{\min} = \frac{1}{2}\sqrt{\log_2 N}$")
    ax2.axhline(12, color="#2e7d32", ls="--", lw=1.8, label=r"ML-KEM / Kyber NTT ($q = 3329$, fixed $12$ bits)")
    ax2.axhline(23, color="#6a1b9a", ls="-.", lw=1.8, label=r"ML-DSA / Dilithium NTT ($q = 8380417$, fixed $23$ bits)")
    ax2.scatter([576], [12.0], color="#2e7d32", s=55, zorder=5, edgecolor="black", lw=0.7)
    ax2.annotate(r"Kyber crossover ($k=576$)", xy=(576, 12.0), xytext=(22, 14.5), fontsize=8.0,
                 arrowprops=dict(arrowstyle="->", lw=0.8, color="#1b5e20"))
    ax2.set_xlabel(r"Transform scale $k = \log_2 N$")
    ax2.set_ylabel(r"Required scalar coefficient bit-width $b = \log_2 C$")
    ax2.set_ylim(0, 26.5)
    ax2.set_title("(b) Complex-FFT Blow-Up vs. Fixed-Modulus NTT Dichotomy")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=7.6)

    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGDIR / "fig1_morgenstern_conservation.png", bbox_inches="tight")
    plt.close(fig)


def make_fig2() -> None:
    d = json.loads((RESULTS / "exp3_pythagorean_separation.json").read_text(encoding="utf-8"))
    pts = d["pythagorean_points"]
    Ls = [p["L_float"] for p in pts]
    deltas = [p["delta_float"] for p in pts]
    lbs = [p["lower_bound_float"] for p in pts]
    ubs = [p["upper_bound_float"] for p in pts]
    ratios = [p["ratio_delta_over_half_L2"] for p in pts]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.2), constrained_layout=True)

    ax1.loglog(Ls, ubs, "--", color="#c62828", lw=1.6, label=r"Upper bound $L^2 / 2$")
    ax1.loglog(Ls, deltas, "o-", color="#1565c0", lw=2.0, ms=4.5,
               label=r"Exact Pythagorean $\Delta_{\mathrm{rect}}(L) = \frac{2v^2}{u^2-v^2}$")
    ax1.loglog(Ls, lbs, "-.", color="#2e7d32", lw=1.6, label=r"Lower bound $L^2 / (2 + L)$")
    ax1.set_xlabel(r"Pythagorean rectangle height $L = 2uv/(u^2 - v^2)$")
    ax1.set_ylabel(r"Fourier-vs-permutation separation $\sqrt{1+L^2} - 1$")
    ax1.set_title(r"(a) Exact Two-Sided Rational Separation Envelope")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.92, fontsize=7.8)

    ax2.plot(Ls, ratios, "s-", color="#6a1b9a", lw=2.0, ms=4.8,
             label=r"Exact ratio $\Delta_{\mathrm{rect}}(L) / (L^2/2)$")
    ax2.plot(Ls, [2.0 / (2.0 + L) for L in Ls], "--", color="#2e7d32", lw=1.5,
             label=r"Algebraic lower envelope $2 / (2 + L)$")
    ax2.axhline(1.0, color="black", ls=":", lw=1.2, label=r"Asymptotic limit $1$ ($L \to 0$)")
    ax2.set_xlim(0.0, 1.4)
    ax2.set_ylim(0.55, 1.04)
    ax2.set_xlabel(r"Pythagorean rectangle height $L$")
    ax2.set_ylabel(r"Normalized separation $\Delta_{\mathrm{rect}}(L) / (L^2 / 2)$")
    ax2.set_title(r"(b) Convergence to $\frac{1}{2} L^2$ Separation Law")
    ax2.legend(loc="lower left", frameon=True, framealpha=0.92, fontsize=7.8)

    fig.savefig(FIGDIR / "fig2_pythagorean_separation.png", bbox_inches="tight")
    plt.close(fig)


def make_fig3() -> None:
    d1 = json.loads((RESULTS / "exp1_certified_atlas.json").read_text(encoding="utf-8"))
    d4 = json.loads((RESULTS / "exp4_crossover_and_ntt.json").read_text(encoding="utf-8"))
    cross = d4["crossovers"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.2), constrained_layout=True)

    # Panel (a): Finite-N crossover scale k* = c0^2
    c0s = [c["overhead_c0"] for c in cross]
    kstars = [c["crossover_k_log2N"] for c in cross]
    bars = ax1.bar([str(c) for c in c0s], kstars, color="#1565c0", edgecolor="black", lw=0.7, width=0.55)
    for b, kst in zip(bars, kstars):
        ax1.text(b.get_x() + b.get_width() / 2, kst + 6, rf"$k^*={kst}$" + f"\n($N=2^{{{kst}}}$)",
                 ha="center", va="bottom", fontsize=7.6)
    ax1.set_ylim(0, 310)
    ax1.set_xlabel(r"Sub-logarithmic circuit constant overhead $c_0$")
    ax1.set_ylabel(r"Crossover scale $k^* = \log_2 N^* = c_0^2$")
    ax1.set_title(r"(a) Exact Finite-$N$ Crossover $c_0 \sqrt{\log_2 N} < \log_2 N$")

    # Panel (b): Certified exact DAG circuit verification times across Hadamard & NTT certificates
    dag_certs = [c for c in d1["certificates"] if c["mode"] in ("exact_hadamard_circuit_q", "exact_ntt_circuit_fq")]
    names = [
        r"$H_4$ ($\mathbb{Q}$)",
        r"$H_8$ ($\mathbb{Q}$)",
        r"$H_{16}$ ($\mathbb{Q}$)",
        r"$\mathbb{F}_{17}$ ($N=4$)",
        r"$\mathbb{F}_{17}$ ($N=8$)",
        r"$\mathbb{F}_{257}$ ($N=16$)",
        r"Kyber $\mathbb{F}_{3329}$ ($N=8$)",
        r"Kyber $\mathbb{F}_{3329}$ ($N=16$)",
    ]
    gates = [c["gate_count"] for c in dag_certs]
    times = [c["verify_ms"] for c in dag_certs]
    cols = ["#2e7d32" if "H_" in n else ("#c62828" if "Kyber" in n else "#ef6c00") for n in names]
    y = np.arange(len(names))
    ax2.barh(y, times, color=cols, edgecolor="black", lw=0.7, height=0.6)
    for idx, (tm, gt) in enumerate(zip(times, gates)):
        ax2.text(tm + 0.06, idx, f"{tm:.2f} ms ({gt} gates)", va="center", ha="left", fontsize=7.8)
    ax2.set_yticks(y)
    ax2.set_yticklabels(names, fontsize=8.2)
    ax2.set_xlim(0, max(times) * 1.55)
    ax2.set_xlabel("Exact zero-float DAG verification time (ms)")
    ax2.set_title("(b) Exact Straight-Line Circuit DAG Certification (Red: Kyber)")

    fig.savefig(FIGDIR / "fig3_crossover_and_ntt_certs.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    make_fig1()
    make_fig2()
    make_fig3()
    print("[FIGURES] Generated 3 publication-grade 300-DPI figures in paper/figures/.")


if __name__ == "__main__":
    main()
