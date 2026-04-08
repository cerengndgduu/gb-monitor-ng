"""
GB Grid Monitor
===============
Fetches live UK electricity grid data from the National Energy System
Operator (NESO) Carbon Intensity API and visualises:

  - Current generation mix (by fuel type)
  - Carbon intensity rating and forecast vs actual
  - Today's half-hourly carbon intensity trend

Data source: https://api.carbonintensity.org.uk  (public, no auth required)

Usage
-----
    python grid_monitor.py              # print summary to terminal
    python grid_monitor.py --plot       # also save plot as grid_monitor.png
    python grid_monitor.py --plot --show  # open plot interactively

Author: Ceren Gundogdu
"""

import argparse
import sys
from datetime import datetime

import requests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
BASE = "https://api.carbonintensity.org.uk"
EP_INTENSITY  = f"{BASE}/intensity"
EP_GENERATION = f"{BASE}/generation"
EP_TREND      = f"{BASE}/intensity/date"

# Fuel colour palette (matches National Grid colour conventions where possible)
FUEL_COLOURS = {
    "wind":    "#1D9E75",
    "solar":   "#EF9F27",
    "nuclear": "#7F77DD",
    "gas":     "#D85A30",
    "coal":    "#888780",
    "hydro":   "#378ADD",
    "biomass": "#639922",
    "imports": "#D4537E",
    "other":   "#B4B2A9",
}

RENEWABLE_FUELS = {"wind", "solar", "hydro", "biomass"}
FOSSIL_FUELS    = {"gas", "coal"}

# Carbon intensity thresholds (gCO2eq/kWh) for rating display
INDEX_THRESHOLDS = {
    "very low": (0,   50),
    "low":      (50,  100),
    "moderate": (100, 200),
    "high":     (200, 300),
    "very high":(300, float("inf")),
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch(url: str) -> dict:
    """GET *url* and return parsed JSON, raising on HTTP errors."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [error] Could not reach {url}: {e}", file=sys.stderr)
        sys.exit(1)


def get_intensity() -> dict:
    """Return current half-hour carbon intensity data point."""
    return fetch(EP_INTENSITY)["data"][0]


def get_generation_mix() -> list[dict]:
    """Return current generation mix as a list of {fuel, perc} dicts."""
    return fetch(EP_GENERATION)["data"][0]["generationmix"]


def get_daily_trend() -> list[dict]:
    """Return today's half-hourly intensity data points."""
    return fetch(EP_TREND)["data"]


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def compute_mix_summary(mix: list[dict]) -> dict:
    """Compute renewable, fossil, and low-carbon percentages from mix list."""
    totals = {f["fuel"]: f["perc"] for f in mix}
    renewable = sum(totals.get(f, 0) for f in RENEWABLE_FUELS)
    fossil    = sum(totals.get(f, 0) for f in FOSSIL_FUELS)
    low_carbon = renewable + totals.get("nuclear", 0)
    return {"renewable": renewable, "fossil": fossil, "low_carbon": low_carbon}


def trend_stats(trend: list[dict]) -> dict:
    """Return min, max, and average intensity from the daily trend."""
    vals = [
        pt["intensity"]["actual"] or pt["intensity"]["forecast"]
        for pt in trend
        if pt.get("intensity")
    ]
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"min": None, "max": None, "avg": None}
    return {
        "min": min(vals),
        "max": max(vals),
        "avg": round(sum(vals) / len(vals)),
    }


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

def print_summary(intensity: dict, mix: list[dict], trend: list[dict]) -> None:
    """Print a formatted summary to stdout."""
    val   = intensity["intensity"]["actual"] or intensity["intensity"]["forecast"]
    fc    = intensity["intensity"]["forecast"]
    idx   = intensity["intensity"]["index"]
    ts    = intensity["from"]

    summary = compute_mix_summary(mix)
    stats   = trend_stats(trend)

    sorted_mix = sorted(mix, key=lambda x: x["perc"], reverse=True)

    bar_width = 30

    print()
    print("=" * 56)
    print("  GB Grid Monitor  —  National Energy System Operator")
    print("=" * 56)
    print(f"  Timestamp : {ts}  (UTC)")
    print()
    print("  CARBON INTENSITY")
    print(f"    Current  : {val} gCO\u2082eq/kWh  [{idx.upper()}]")
    print(f"    Forecast : {fc} gCO\u2082eq/kWh")
    print()
    print("  GENERATION MIX")
    for f in sorted_mix:
        fuel = f["fuel"].ljust(9)
        pct  = f["perc"]
        bar  = "#" * round(pct / 100 * bar_width)
        print(f"    {fuel}  {bar:<{bar_width}}  {pct:5.1f}%")
    print()
    print("  MIX SUMMARY")
    print(f"    Renewables  : {summary['renewable']:.1f}%")
    print(f"    Fossil      : {summary['fossil']:.1f}%")
    print(f"    Low-carbon  : {summary['low_carbon']:.1f}%")
    print()
    print("  TODAY'S TREND")
    print(f"    Min : {stats['min']} gCO\u2082eq/kWh")
    print(f"    Max : {stats['max']} gCO\u2082eq/kWh")
    print(f"    Avg : {stats['avg']} gCO\u2082eq/kWh")
    print()
    print("  Source: api.carbonintensity.org.uk")
    print("=" * 56)
    print()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def build_plot(
    intensity: dict,
    mix: list[dict],
    trend: list[dict],
    save_path: str = "grid_monitor.png",
    show: bool = False,
) -> None:
    """Build and save (or show) a two-panel matplotlib figure."""

    val = intensity["intensity"]["actual"] or intensity["intensity"]["forecast"]
    idx = intensity["intensity"]["index"]
    ts  = intensity["from"]

    summary    = compute_mix_summary(mix)
    stats      = trend_stats(trend)
    sorted_mix = sorted(mix, key=lambda x: x["perc"], reverse=True)

    # Extract trend values and time labels
    trend_vals  = [
        pt["intensity"]["actual"] or pt["intensity"]["forecast"]
        for pt in trend
        if pt.get("intensity")
    ]
    trend_times = list(range(len(trend_vals)))  # half-hour slots (0–47)
    hour_ticks  = list(range(0, len(trend_vals), 4))   # every 2 hours
    hour_labels = [f"{i // 2:02d}:00" for i in hour_ticks]

    # --- Figure setup --------------------------------------------------
    fig = plt.figure(figsize=(14, 7), facecolor="#0d1318")
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.12, wspace=0.35)

    gs  = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1, 1.4])
    ax1 = fig.add_subplot(gs[0])   # generation mix
    ax2 = fig.add_subplot(gs[1])   # intensity trend

    for ax in (ax1, ax2):
        ax.set_facecolor("#111a22")
        for spine in ax.spines.values():
            spine.set_edgecolor("#1a2e3a")
            spine.set_linewidth(0.5)
        ax.tick_params(colors="#4a6878", labelsize=8)
        ax.xaxis.label.set_color("#4a6878")
        ax.yaxis.label.set_color("#4a6878")

    TEXT_PRI  = "#c0d8e4"
    TEXT_SEC  = "#4a6878"
    ACCENT    = "#1D9E75"

    # --- Panel 1: Generation mix bar chart ----------------------------
    fuels = [f["fuel"] for f in sorted_mix]
    percs = [f["perc"] for f in sorted_mix]
    colors = [FUEL_COLOURS.get(f, "#888") for f in fuels]

    bars = ax1.barh(fuels, percs, color=colors, height=0.6, edgecolor="none")
    ax1.set_xlabel("% of generation mix", color=TEXT_SEC, fontsize=8)
    ax1.set_xlim(0, max(percs) * 1.25)
    ax1.invert_yaxis()
    ax1.tick_params(axis="y", labelsize=8, colors=TEXT_PRI)
    ax1.tick_params(axis="x", labelsize=7, colors=TEXT_SEC)

    for bar, pct in zip(bars, percs):
        ax1.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%", va="center", ha="left",
            color=TEXT_SEC, fontsize=7, fontfamily="monospace",
        )

    # Mix summary annotation
    ax1.text(
        0.98, 0.02,
        f"Renewables  {summary['renewable']:.1f}%\n"
        f"Low-carbon  {summary['low_carbon']:.1f}%\n"
        f"Fossil fuel  {summary['fossil']:.1f}%",
        transform=ax1.transAxes, ha="right", va="bottom",
        fontsize=7, fontfamily="monospace", color=TEXT_SEC,
        linespacing=1.6,
    )

    ax1.set_title("Generation mix — current half hour",
                  color=TEXT_SEC, fontsize=8, pad=10, loc="left")

    # --- Panel 2: Carbon intensity trend ------------------------------
    ax2.fill_between(trend_times, trend_vals, alpha=0.12, color=ACCENT)
    ax2.plot(trend_times, trend_vals, color=ACCENT, linewidth=1.5, solid_capstyle="round")

    # Highlight current slot
    if trend_vals:
        ax2.scatter(trend_times[-1], trend_vals[-1], color=ACCENT, s=30, zorder=5)

    # Min / max annotations
    if stats["min"] is not None:
        min_idx = trend_vals.index(stats["min"])
        max_idx = trend_vals.index(stats["max"])
        ax2.annotate(f"min {stats['min']}", xy=(min_idx, stats["min"]),
                     xytext=(min_idx + 1, stats["min"] - 8),
                     color="#1D9E75", fontsize=7, fontfamily="monospace")
        ax2.annotate(f"max {stats['max']}", xy=(max_idx, stats["max"]),
                     xytext=(max_idx + 1, stats["max"] + 4),
                     color="#D85A30", fontsize=7, fontfamily="monospace")

    ax2.set_xlabel("Time (UTC)", color=TEXT_SEC, fontsize=8)
    ax2.set_ylabel("gCO\u2082eq/kWh", color=TEXT_SEC, fontsize=8)
    ax2.set_xticks(hour_ticks)
    ax2.set_xticklabels(hour_labels, fontsize=7)
    ax2.set_xlim(0, max(trend_times) if trend_times else 47)
    ax2.grid(axis="y", color="#1a2e3a", linewidth=0.5)

    # Current reading annotation
    ax2.text(
        0.98, 0.97,
        f"{val} gCO\u2082eq/kWh\n{idx.upper()}",
        transform=ax2.transAxes, ha="right", va="top",
        fontsize=9, fontfamily="monospace",
        color=ACCENT, linespacing=1.5,
    )

    ax2.set_title("Carbon intensity — today (30-min intervals)",
                  color=TEXT_SEC, fontsize=8, pad=10, loc="left")

    # --- Figure title and footer --------------------------------------
    fig.text(
        0.5, 0.95,
        "GB Grid Monitor  —  National Energy System Operator",
        ha="center", color=TEXT_PRI, fontsize=13, fontweight="bold",
    )
    fig.text(
        0.5, 0.91,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC  |  "
        "Source: api.carbonintensity.org.uk",
        ha="center", color=TEXT_SEC, fontsize=7, fontfamily="monospace",
    )

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"  Plot saved → {save_path}")

    if show:
        plt.show()

    plt.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and display live UK grid generation and carbon intensity data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Save a matplotlib plot to grid_monitor.png",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Open the plot interactively (requires --plot)",
    )
    parser.add_argument(
        "--output", default="grid_monitor.png",
        help="Output path for the plot (default: grid_monitor.png)",
    )
    args = parser.parse_args()

    print("  Fetching data from NESO Carbon Intensity API…")
    intensity = get_intensity()
    mix       = get_generation_mix()
    trend     = get_daily_trend()

    print_summary(intensity, mix, trend)

    if args.plot or args.show:
        build_plot(intensity, mix, trend, save_path=args.output, show=args.show)


if __name__ == "__main__":
    main()
