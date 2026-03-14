#!/usr/bin/env python3
"""
SKYFALL Result Visualizer
Reproduces Figures 10-14 from the NDSS 2025 paper:
  "Time-varying Bottleneck Links in LEO Satellite Networks:
   Identification, Exploits, and Countermeasures"

Usage:
  python3 visualize_results.py
Output:
  figures/ directory with one PNG per paper figure
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Paths ────────────────────────────────────────────────────────────────────

RESULTS = "starlink_shell_one/results"
OUT_DIR = "figures"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_floats(path):
    with open(path) as f:
        return [float(line.strip()) for line in f if line.strip()]

def load_key_value(path):
    """Parse files like  '0.1: 446.0'  into (keys, values)."""
    keys, vals = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            k, v = line.split(":")
            keys.append(float(k.strip()))
            vals.append(float(v.strip()))
    return keys, vals

def pct_labels(keys):
    """Convert ratio keys like 0.1 → '10%'."""
    return [f"{int(round(k*100))}%" for k in keys]

STYLE = {
    "skyfall": dict(color="#d62728", marker="^", linewidth=1.8, markersize=6, label="SKYFALL"),
    "icarus":  dict(color="#1f77b4", marker="^", linewidth=1.8, markersize=6, label="ICARUS"),
    "traffic": dict(color="#2ca02c", linestyle="--", linewidth=1.5, label="Background traffic"),
    "gsl":     dict(color="#ff7f0e", linewidth=1.5),
}

# ── Figure 10a ───────────────────────────────────────────────────────────────

def plot_fig10a():
    traffic = load_floats(f"{RESULTS}/fig-10a/ratio_of_reduced_background_traffic_by_skyfall.txt")
    gsls    = load_floats(f"{RESULTS}/fig-10a/ratio_of_attacked_GSLs_by_skyfall.txt")
    t = range(len(traffic))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(t, traffic, color="#d62728", linewidth=1.2,
            label="Ratio of reduced legal traffic by SKYFALL")
    ax.plot(t, gsls, color="#ff7f0e", linewidth=1.2,
            label="Ratio of congested GSLs by SKYFALL")
    ax.set_xlabel("Time slot (s)")
    ax.set_ylabel("Ratio")
    ax.set_ylim(0, 1)
    ax.set_xlim(0, len(traffic) - 1)
    ax.annotate("Reducing significant background traffic\nthrough targeting a few GSLs",
                xy=(len(traffic)//2, np.mean(traffic)),
                xytext=(len(traffic)//2 - 400, 0.6),
                arrowprops=dict(arrowstyle="->", color="red"),
                color="red", fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title("Fig. 10(a): Risks on Starlink's legal traffic and GSLs by SKYFALL")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-10a.png", dpi=150)
    plt.close(fig)
    print("Saved fig-10a.png")

# ── Figure 10b ───────────────────────────────────────────────────────────────

def plot_fig10b():
    traffic = load_floats(f"{RESULTS}/fig-10b/ratio_of_reduced_background_traffic_by_icarus.txt")
    gsls    = load_floats(f"{RESULTS}/fig-10b/ratio_of_attacked_GSLs_by_icarus.txt")
    t = range(len(traffic))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(t, traffic, color="#d62728", linewidth=1.2,
            label="Ratio of reduced legal traffic by ICARUS")
    ax.plot(t, gsls, color="#ff7f0e", linewidth=1.2,
            label="Ratio of congested GSLs by ICARUS")
    ax.set_xlabel("Time slot (s)")
    ax.set_ylabel("Ratio")
    ax.set_ylim(0, 1)
    ax.set_xlim(0, len(traffic) - 1)
    ax.annotate("Reducing a small number of legal traffic\nthrough a few GSLs",
                xy=(len(traffic)//2, np.mean(traffic)),
                xytext=(len(traffic)//2 - 400, 0.5),
                arrowprops=dict(arrowstyle="->", color="red"),
                color="red", fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title("Fig. 10(b): Risks on Starlink's legal traffic and GSLs by ICARUS")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-10b.png", dpi=150)
    plt.close(fig)
    print("Saved fig-10b.png")

# ── Figure 10c ───────────────────────────────────────────────────────────────

def plot_fig10c():
    bg      = load_floats(f"{RESULTS}/fig-10c/background_traffic_without_attack.txt")
    skyfall = load_floats(f"{RESULTS}/fig-10c/actual_throughput_skyfall_after_aggregation.txt")
    icarus  = load_floats(f"{RESULTS}/fig-10c/actual_throughput_icarus.txt")
    t = range(len(bg))

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(t, bg,      color="#2ca02c", linestyle="--", linewidth=1.5,
            label="Original background traffic without congestion")
    ax.plot(t, icarus,  color="#1f77b4", linewidth=1.2,
            label="Actual legal traffic throughput under ICARUS's congestion")
    ax.plot(t, skyfall, color="#d62728", linewidth=1.2,
            label="Actual legal traffic throughput under SKYFALL's congestion")
    ax.set_xlabel("Time slot (s)")
    ax.set_ylabel("Throughput (Gbps)")
    ax.set_xlim(0, len(bg) - 1)
    ax.legend(fontsize=7.5)
    ax.set_title("Fig. 10(c): Throughput change on Starlink")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-10c.png", dpi=150)
    plt.close(fig)
    print("Saved fig-10c.png")

# ── Figure 11a ───────────────────────────────────────────────────────────────

def plot_fig11a():
    data = load_floats(f"{RESULTS}/fig-11a/number_attacked_GSLs_starlink_cdf.txt")
    n = len(data)
    cdf = np.arange(1, n + 1) / n

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(data, cdf, color="#d62728", linewidth=1.8, label="Starlink")
    ax.set_xlabel("Number of congested GSLs")
    ax.set_ylabel("CDF")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9)
    ax.set_title("Fig. 11(a): CDF of congested GSLs by SKYFALL")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-11a.png", dpi=150)
    plt.close(fig)
    print("Saved fig-11a.png")

# ── Figure 11b ───────────────────────────────────────────────────────────────

def plot_fig11b():
    data = load_floats(f"{RESULTS}/fig-11a/number_attacked_GSLs_starlink_cdf.txt")

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.boxplot([data], tick_labels=["Starlink"], patch_artist=True,
               boxprops=dict(facecolor="#d62728", alpha=0.4),
               medianprops=dict(color="black", linewidth=2))
    ax.set_ylabel("Number of congested GSLs")
    ax.set_title("Fig. 11(b): Box-plot of congested GSLs by SKYFALL")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-11b.png", dpi=150)
    plt.close(fig)
    print("Saved fig-11b.png")

# ── Figure 12a ───────────────────────────────────────────────────────────────

def plot_fig12a():
    ks, vs_sky = load_key_value(f"{RESULTS}/fig-12a/botnet_size_for_skyfall.txt")
    _,  vs_ica = load_key_value(f"{RESULTS}/fig-12a/botnet_size_for_icarus.txt")
    # Paper: X = number of UTs, Y = throughput degradation (%)
    pcts = [k * 100 for k in ks]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(vs_sky, pcts, **{**STYLE["skyfall"]})
    ax.plot(vs_ica, pcts, **{**STYLE["icarus"]})
    ax.set_xlabel("Number of available compromised UTs")
    ax.set_ylabel("Throughput degradation (%)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 55)
    ax.legend(fontsize=9)
    ax.set_title("Fig. 12(a): Throughput degradation under +Grid topology")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-12a.png", dpi=150)
    plt.close(fig)
    print("Saved fig-12a.png")

# ── Figure 12b ───────────────────────────────────────────────────────────────

def plot_fig12b():
    ks, vs_sky = load_key_value(f"{RESULTS}/fig-12b/botnet_size_for_skyfall.txt")
    _,  vs_ica = load_key_value(f"{RESULTS}/fig-12b/botnet_size_for_icarus.txt")
    pcts = [k * 100 for k in ks]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(vs_sky, pcts, **{**STYLE["skyfall"]})
    ax.plot(vs_ica, pcts, **{**STYLE["icarus"]})
    ax.set_xlabel("Number of available compromised UTs")
    ax.set_ylabel("Throughput degradation (%)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 55)
    ax.legend(fontsize=9)
    ax.set_title("Fig. 12(b): Throughput degradation under Circular topology")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-12b.png", dpi=150)
    plt.close(fig)
    print("Saved fig-12b.png")

# ── Figure 13a ───────────────────────────────────────────────────────────────

def plot_fig13a():
    ks, vs_sky = load_key_value(f"{RESULTS}/fig-13a/number_blocks_skyfall_+grid.txt")
    _,  vs_ica = load_key_value(f"{RESULTS}/fig-13a/number_blocks_icarus_+grid.txt")
    # Paper: X = number of blocks, Y = throughput degradation (%)
    pcts = [k * 100 for k in ks]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(vs_sky, pcts, **{**STYLE["skyfall"]})
    ax.plot(vs_ica, pcts, **{**STYLE["icarus"]})
    ax.set_xlabel("Number of regional blocks")
    ax.set_ylabel("Throughput degradation (%)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 55)
    ax.legend(fontsize=9)
    ax.set_title("Fig. 13(a): Throughput degradation with varying blocks (+Grid)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-13a.png", dpi=150)
    plt.close(fig)
    print("Saved fig-13a.png")

# ── Figure 13b ───────────────────────────────────────────────────────────────

def plot_fig13b():
    ks, vs_sky = load_key_value(f"{RESULTS}/fig-13b/number_blocks_skyfall_circle.txt")
    _,  vs_ica = load_key_value(f"{RESULTS}/fig-13b/number_blocks_icarus_circle.txt")
    pcts = [k * 100 for k in ks]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(vs_sky, pcts, **{**STYLE["skyfall"]})
    ax.plot(vs_ica, pcts, **{**STYLE["icarus"]})
    ax.set_xlabel("Number of regional blocks")
    ax.set_ylabel("Throughput degradation (%)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 55)
    ax.legend(fontsize=9)
    ax.set_title("Fig. 13(b): Throughput degradation with varying blocks (Circular)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig-13b.png", dpi=150)
    plt.close(fig)
    print("Saved fig-13b.png")

# ── Figure 14 helper ─────────────────────────────────────────────────────────

def _plot_fig14(subdir, topology_label, out_name):
    base = f"{RESULTS}/{subdir}"
    degradation_levels = [10, 20, 30, 40, 50]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b"]

    bg = load_floats(f"{base}/background_traffic.txt")
    n = len(bg)
    bg_cdf = np.arange(1, n + 1) / n

    fig, ax = plt.subplots(figsize=(6, 4.5))

    for pct, color in zip(degradation_levels, colors):
        data = load_floats(f"{base}/malicious_uplink_throughput_degradation_{pct}_percent.txt")
        cdf  = np.arange(1, len(data) + 1) / len(data)
        ax.plot(data, cdf, color=color, linewidth=1.5,
                label=f"Throughput degradation={pct}%")

    ax.plot(bg, bg_cdf, color="#2ca02c", linestyle="--", linewidth=1.5,
            label="Background traffic")

    ax.set_xlabel("Malicious uplink throughput of a satellite (Mbps)")
    ax.set_ylabel("CDF")
    ax.set_xlim(left=0)
    ax.set_ylim(0.9, 1.0)
    ax.legend(fontsize=8)
    ax.set_title(f"Fig. {out_name[-4:]}: Detectability under {topology_label} Topology")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/{out_name}.png", dpi=150)
    plt.close(fig)
    print(f"Saved {out_name}.png")

def plot_fig14a():
    _plot_fig14("fig-14a", "+Grid", "fig-14a")

def plot_fig14b():
    _plot_fig14("fig-14b", "Circular", "fig-14b")

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Writing figures to ./{OUT_DIR}/\n")
    plot_fig10a()
    plot_fig10b()
    plot_fig10c()
    plot_fig11a()
    plot_fig11b()
    plot_fig12a()
    plot_fig12b()
    plot_fig13a()
    plot_fig13b()
    plot_fig14a()
    plot_fig14b()
    print(f"\nDone. All figures saved to ./{OUT_DIR}/")
