"""Static charts saved to docs/figures/. Observed/derived = solid fills; estimates/scenarios = hatched + dashed."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from .paths import FIGURES

OBS = "#2a6fb0"      # observed / derived
EST = "#d98a1f"      # estimate / scenario
COST = "#7a7f87"
INK = "#222222"
plt.rcParams.update({
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11, "figure.dpi": 100, "savefig.dpi": 160,
    "savefig.bbox": "tight", "axes.edgecolor": "#555555",
})
EST_STYLE = dict(hatch="///", edgecolor=EST, facecolor="white", linewidth=1.2, linestyle="--")


def _save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_event_pnl(res):
    pnl = res["event_pnl"].set_index("event_id")
    sc = res["s26_scenarios"]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    w = 0.26
    groups = ["F24", "S25", "S26"]
    for i, e in enumerate(["F24", "S25"]):
        r = pnl.loc[e]
        for j, (v, c) in enumerate([(r.revenue_usd, OBS), (r.cost_usd, COST), (r.net_usd, "#2f8f5b")]):
            ax.bar(i + (j - 1) * w, v, w, color=c)
            ax.text(i + (j - 1) * w, v + 6, f"${v:,.0f}", ha="center", fontsize=9)
    # S26: revenue observed (pre-orders only); cost and net are scenario ranges (hatched)
    i = 2
    rev = 375.0
    ax.bar(i - w, rev, w, color=OBS)
    ax.text(i - w, rev + 6, "$375", ha="center", fontsize=9)
    cost_mid, cost_lo, cost_hi = sc.cost_pre_orders_only.iloc[0], sc.cost_pre_orders_only.min(), sc.cost_pre_orders_only.max()
    net_mid, net_lo, net_hi = sc.net_pre_orders_only.iloc[0], sc.net_pre_orders_only.min(), sc.net_pre_orders_only.max()
    for off, mid, lo, hi in [(0, cost_mid, cost_lo, cost_hi), (w, net_mid, net_lo, net_hi)]:
        ax.bar(i + off, mid, w, **EST_STYLE)
        ax.errorbar(i + off, mid, yerr=[[mid - lo], [hi - mid]], color=INK, capsize=4, lw=1.2)
        ax.text(i + off, hi + 8, f"${lo:,.0f}–{hi:,.0f}", ha="center", fontsize=8.5, color=EST)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["F24 (observed)", "S25 (observed)", "S26 (pre-order revenue observed;\ncost & net = ESTIMATE range)"])
    ax.set_ylabel("USD")
    ax.set_title("Event P&L: observed events vs S26 scenario estimate")
    ax.set_ylim(0, 640)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (OBS, COST, "#2f8f5b")] + \
              [plt.Rectangle((0, 0), 1, 1, **EST_STYLE)]
    ax.legend(handles, ["Revenue", "Cost", "Net (derived)", "ESTIMATE (bar = cost scenario A; whiskers = A–D range)"],
              fontsize=8, loc="upper right", frameon=False)
    return _save(fig, "event_pnl.png")


def fig_cost_structure(res):
    cs = res["cost_structure"]
    cats = ["ingredients", "supplies", "printing", "market_research"]
    colors = ["#2a6fb0", "#6fa8dc", "#9aa0a6", "#c9a227"]
    fig, ax = plt.subplots(figsize=(8, 2.9))
    for y, e in enumerate(["S25", "F24"]):
        left = 0
        d = cs[cs.event_id == e].set_index("category")
        for c, col in zip(cats, colors):
            share = float(d.share.get(c, 0))
            if share > 0:
                ax.barh(y, share, left=left, color=col, label=c.replace("_", " "))
                ax.text(left + share / 2, y, f"{share:.0%}\n${d.cost_usd[c]:,.0f}", ha="center", va="center", fontsize=8.5, color="white")
            left += share
    ax.set_yticks([0, 1])
    ax.set_yticklabels([f"S25  (${cs[cs.event_id=='S25'].cost_usd.sum():,.2f})", f"F24  (${cs[cs.event_id=='F24'].cost_usd.sum():,.2f})"])
    ax.set_xlabel("Share of planned fundraiser cost (observed; F24 parking fine excluded)")
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    h, l = ax.get_legend_handles_labels()
    seen = dict(zip(l, h))
    ax.legend(seen.values(), seen.keys(), ncol=4, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    ax.set_title("Cost structure by event")
    return _save(fig, "cost_structure.png")


def fig_order_sizes(res):
    d = res["demand"]["size_distribution"]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = np.arange(len(d))
    ax.bar(x, d.n_orders, color=OBS)
    for xi, r in zip(x, d.itertuples()):
        ax.text(xi, r.n_orders + 0.3, f"{r.n_orders} orders\n{r.units} items", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(d.quantity)
    ax.set_xlabel("Items per order")
    ax.set_ylabel("Number of orders")
    ax.set_ylim(0, d.n_orders.max() + 4)
    ax.set_title("S26 order-size distribution (observed, 29 orders)")
    return _save(fig, "order_size_distribution.png")


def fig_concentration(res):
    d = res["demand"]
    c = d["concentration"].set_index("view")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    big_u, big_r = d["largest_units_share"], d["largest_revenue_share"]
    ax.bar([0, 1], [1 - big_u, 1 - big_r], color=OBS, label="other 28 orders")
    ax.bar([0, 1], [big_u, big_r], bottom=[1 - big_u, 1 - big_r], color="#c0392b", label="largest order (28 items, $100)")
    ax.text(0, 1 - big_u / 2, f"{big_u:.1%}", ha="center", va="center", color="white", fontsize=9)
    ax.text(1, 1 - big_r / 2, f"{big_r:.1%}", ha="center", va="center", color="white", fontsize=9)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Items (104)", "Revenue ($375)"])
    ax.set_ylim(0, 1); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_ylabel("Share"); ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_title("Largest order's share")
    ax = axes[1]
    labels = ["All orders", "Without\nlargest"]
    vals = [c.loc["all orders", "hhi_units"], c.loc["without largest order", "hhi_units"]]
    base = [c.loc["all orders", "equal_orders_hhi"], c.loc["without largest order", "equal_orders_hhi"]]
    ax.bar([0, 1], vals, color=OBS)
    for i, (v, b) in enumerate(zip(vals, base)):
        ax.text(i, v + 0.003, f"{v:.3f}", ha="center", fontsize=9)
        ax.hlines(b, i - 0.4, i + 0.4, color=INK, linestyles="--", lw=1)
    ax.text(1.45, base[1], "1/n if all\norders equal", fontsize=7.5, va="center")
    ax.set_xticks([0, 1]); ax.set_xticklabels(labels); ax.set_ylabel("Herfindahl index (items), 0–1")
    ax.set_xlim(-0.5, 2.1)
    ax.set_title("Order concentration (HHI)")
    fig.suptitle("S26 demand concentration (derived from observed orders)", y=1.02, fontweight="bold")
    return _save(fig, "concentration.png")


def fig_timing(res):
    d = res["demand"]
    tl = d["timeline"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    ax.step(tl.ts, tl.cum_orders, where="post", color=OBS, label="Cumulative orders")
    ax.step(tl.ts, tl.cum_units, where="post", color="#2f8f5b", label="Cumulative items")
    ax.set_ylabel("Count (observed)")
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.axvspan(np.datetime64("2026-03-02"), np.datetime64("2026-03-04"), color=EST, alpha=0.10)
    ax.text(np.datetime64("2026-03-02T01:00"), 52, "Mar 2–3: second\nwave (pattern only;\ncause not known)", fontsize=8, color="#8a5a10")
    ax.set_xlabel("Order timestamp (as recorded; timezone unknown)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Cumulative S26 pre-orders")
    ax = axes[1]
    h = d["by_hour"]
    ax.bar(h.hour, h.n_orders, color=OBS)
    ax.set_xlabel("Hour of day (as recorded)")
    ax.set_ylabel("Orders")
    ax.set_xticks(range(0, 24, 3))
    ax.set_title("Orders by hour of day")
    return _save(fig, "timing.png")


def fig_s26_scenarios(res):
    sc = res["s26_scenarios"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(sc))
    w = 0.38
    ax.bar(x - w / 2, sc.net_pre_orders_only, w, **EST_STYLE, label="Pre-orders only (cook 104)")
    ax.bar(x + w / 2, sc.net_buffer_expected, w, hatch="..", edgecolor=EST, facecolor="white", linewidth=1.2,
           linestyle=":", label="With 10% buffer: chosen scenario (50% walk-up sell-through)")
    ax.errorbar(x + w / 2, sc.net_buffer_expected,
                yerr=[sc.net_buffer_expected - sc.net_buffer_worst, sc.net_buffer_best - sc.net_buffer_expected],
                fmt="none", color=INK, capsize=4, lw=1.2, label="0% to 100% walk-up sell-through")
    for xi, r in zip(x, sc.itertuples()):
        ax.text(xi - w / 2, r.net_pre_orders_only + 6, f"${r.net_pre_orders_only:,.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.scenario}: ${r.unit_cost_usd:.2f}/item\n({r.cost_confidence})" for r in sc.itertuples()], fontsize=8.5)
    ax.set_xlabel("Cost scenario (cost per item)")
    ax.set_ylabel("Net profit, USD (ESTIMATE)")
    ax.set_ylim(0, 380)
    ax.set_title("S26 net profit ESTIMATES by cost scenario (revenue = observed $375 pre-orders + scenario walk-ups)")
    ax.title.set_fontsize(9.5)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    return _save(fig, "s26_net_scenarios.png")


def fig_sensitivity(res):
    s = res["sensitivity"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    g = s["cost_price"]
    ax = axes[0]
    im = ax.imshow(g.values, origin="lower", aspect="auto", cmap="RdYlGn", vmin=-150, vmax=400)
    ax.set_xticks(range(len(g.columns))); ax.set_xticklabels([f"${c:.2f}" for c in g.columns])
    ax.set_yticks(range(len(g.index))); ax.set_yticklabels([f"${i:.2f}" for i in g.index])
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            ax.text(j, i, f"{g.values[i, j]:,.0f}", ha="center", va="center", fontsize=7.5)
    ax.set_xlabel("Average price per item")
    ax.set_ylabel("Cost per item")
    ax.set_title("Net profit (USD) for 104 items sold: cost vs price\nSCENARIO GRID, not a forecast", fontsize=9.5)
    g2 = s["buffer_sellthrough"]
    ax = axes[1]
    ax.imshow(g2.values, origin="lower", aspect="auto", cmap="RdYlGn", vmin=g2.values.min() - 20, vmax=g2.values.max() + 20)
    ax.set_xticks(range(len(g2.columns))); ax.set_xticklabels([f"{c:.0%}" for c in g2.columns])
    ax.set_yticks(range(len(g2.index))); ax.set_yticklabels([f"{i:.0%}" for i in g2.index])
    for i in range(g2.shape[0]):
        for j in range(g2.shape[1]):
            ax.text(j, i, f"{g2.values[i, j]:,.0f}", ha="center", va="center", fontsize=8)
    ax.set_xlabel("Walk-up sell-through of buffer items (assumed)")
    ax.set_ylabel("Walk-up buffer (% above pre-orders)")
    ax.set_title("Net profit (USD): buffer vs sell-through\n(\\$1.76/item, \\$3.50 walk-up price: SCENARIO GRID)", fontsize=9.5)
    return _save(fig, "sensitivity.png")


def make_all(res) -> list:
    return [f(res) for f in (fig_event_pnl, fig_cost_structure, fig_order_sizes, fig_concentration,
                             fig_timing, fig_s26_scenarios, fig_sensitivity)]
