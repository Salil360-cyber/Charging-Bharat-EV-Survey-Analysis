"""
Charging Bharat: report charts (run after analysis.py and summary.py).
Saves PNGs to 06_analysis/outputs/charts/. All data is SIMULATED.
"""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path("06_analysis/outputs/charts"); OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9a95"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#c9c8c3", "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
NOTE = "Simulated survey data · Charging Bharat · n = {n}"

df = pd.read_csv("06_analysis/outputs/survey_with_segments.csv")
t2b = df["E1"] >= 4
N = len(df)

def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)

def hbar(ax, labels, values, ns=None, color=BLUE, xmax=1.0):
    y = np.arange(len(labels))
    ax.barh(y, values, color=color, height=0.62)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color="#e6e5e0", lw=0.8); ax.set_axisbelow(True)
    for i, v in enumerate(values):
        lab = f"{v:.0%}" + (f"  (n={ns[i]})" if ns is not None else "")
        ax.text(v + xmax * 0.01, i, lab, va="center", fontsize=9, color=INK2)

# 1. QC: why responses were removed
qc = pd.read_excel("05_qc/qc_log.xlsx", sheet_name="summary").set_index("metric")["count"]
reasons = {"Failed attention check": qc["f_attention"], "Speeder (< 1/3 median time)": qc["f_speeder"],
           "Straight-lined all items": qc["f_straight"], "Outside target area": qc["f_outside"],
           "Under 18": qc["f_underage"], "Duplicate submission": qc["f_duplicate"]}
fig, ax = plt.subplots(figsize=(7.5, 3.4))
lab = list(reasons); val = [int(reasons[k]) for k in lab]
ax.barh(lab, val, color=GREY, height=0.62); ax.invert_yaxis()
for i, v in enumerate(val): ax.text(v + 0.3, i, str(v), va="center", fontsize=9, color=INK2)
ax.set_xlabel("Responses flagged")
ax.set_title(f"Quality control: {int(qc['received'])} received → {int(qc['removed'])} removed → {int(qc['clean'])} clean",
             loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.04, "A response can fail more than one check (9 straight-liners also failed the attention check).", fontsize=8, color=INK2)
save(fig, "01_qc_removals.png")

# 2. Purchase intent by group (three panels, same scale)
groups = [("S1", "Age", ["18–24", "25–34", "35–44", "45+"]),
          ("C2", "Can charge at home", ["Yes", "No", "Not sure"]),
          ("G2", "Occupation", None)]
fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, (col, title, order) in zip(axes, groups):
    g = df.groupby(col)["E1"].agg(n="size", intent=lambda s: (s >= 4).mean())
    g = g.loc[order] if order else g.sort_values("intent", ascending=False)
    hbar(ax, list(g.index), g["intent"].values, g["n"].values, xmax=1.0)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
fig.suptitle(f"Share likely to buy an e-scooter in 12 months (top-2-box); overall {t2b.mean():.1%}",
             x=0.01, ha="left", fontsize=12, color=INK)
fig.text(0.01, -0.03, NOTE.format(n=N) + " · all three differences significant (chi-square p < 0.001)", fontsize=8, color=INK2)
save(fig, "02_intent_by_group.png")

# 3. Main barrier (open-ended, keyword-coded)
CODES = {"Service": ["service", "repair"], "Charging": ["charg"], "Price": ["price", "expensive", "cost is high", "upfront"],
         "Resale / battery cost": ["resale", "second-hand", "replacement"], "Safety": ["fire", "safety", "aag"], "Range": ["range", "highway"]}
def code(t):
    t = str(t).lower()
    for k, ws in CODES.items():
        if any(w in t for w in ws): return k
    return "Other"
b = df["F1"].apply(code).value_counts(normalize=True)
fig, ax = plt.subplots(figsize=(7.5, 3.2))
hbar(ax, list(b.index), b.values, xmax=0.4)
ax.set_title("Main barrier to buying an EV (open-ended answers, keyword-coded)", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.04, NOTE.format(n=N), fontsize=8, color=INK2)
save(fig, "03_barriers.png")

# 4. Brand funnel: aware → consider → prefer
f = pd.read_csv("06_analysis/outputs/funnel.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 3.8))
x = np.arange(len(f)); w = 0.26
for i, (col, colr, lab) in enumerate([("aware", BLUE, "Aware"), ("consider", ORANGE, "Would consider"), ("prefer", AQUA, "Would buy first")]):
    bars = ax.bar(x + (i - 1) * w, f[col], width=w - 0.02, color=colr, label=lab)
    if col == "aware":
        for xi, v in zip(x, f[col]): ax.text(xi - w, v + 0.015, f"{v:.0%}", ha="center", fontsize=8, color=INK2)
ax.set_xticks(x, f.index)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
ax.set_ylim(0, 1); ax.grid(axis="y", color="#e6e5e0", lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, ncol=3, loc="upper right")
ax.set_title("Brand funnel (fictional brands A–F): awareness is wide, consideration drops sharply", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.03, NOTE.format(n=N) + " · 'Would buy first' excludes respondents who would buy petrol", fontsize=8, color=INK2)
save(fig, "04_brand_funnel.png")

# 5. Segments: size and intent (two panels, no dual axis)
prof = df.groupby("segment")[[f"B{i}" for i in range(1, 9)]].mean()
tech, skeptic = prof["B7"].idxmax(), prof["B4"].idxmax()
name = lambda s: "Tech Early Adopter" if s == tech else "Infrastructure Skeptic" if s == skeptic else "Budget Commuter"
seg = df.groupby("segment").agg(n=("E1", "size"), intent=("E1", lambda s: (s >= 4).mean()))
seg.index = [name(s) for s in seg.index]
seg = seg.sort_values("intent", ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(11, 2.8))
hbar(axes[0], list(seg.index), (seg["n"] / N).values, seg["n"].values, color=GREY, xmax=0.6)
axes[0].set_title("Share of respondents", loc="left", fontsize=11, color=INK)
hbar(axes[1], list(seg.index), seg["intent"].values, xmax=1.0)
axes[1].set_title("Likely to buy in 12 months", loc="left", fontsize=11, color=INK)
fig.suptitle("Three attitude segments (K-means, k = 3)", x=0.01, ha="left", fontsize=12, color=INK)
fig.text(0.01, -0.05, NOTE.format(n=N) + " · silhouette scores were low for every k (0.11–0.18): segments overlap", fontsize=8, color=INK2)
save(fig, "05_segments.png")
print("Charts saved to", OUT)
