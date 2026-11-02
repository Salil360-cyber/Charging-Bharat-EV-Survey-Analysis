import pandas as pd, numpy as np
from scipy.stats import chi2_contingency
df = pd.read_csv("06_analysis/outputs/survey_with_segments.csv")
out=[]; say=lambda s="": (print(s), out.append(s))
t2b = df.E1 >= 4
say(f"Clean base: {len(df)} | purchase intent (top-2-box, next 12 months): {t2b.mean():.1%}")
for col, name in [("S1","Age"),("C2","Home charging"),("S2","Town"),("G2","Occupation")]:
    g = df.groupby(col).E1.agg(n="size", intent=lambda s: (s>=4).mean())
    p = chi2_contingency(pd.crosstab(df[col], t2b))[1]
    say(f"{name} (chi-square p={p:.3f}): " + "; ".join(f"{k} {r.intent:.0%} (n={int(r.n)})" for k, r in g.iterrows()))
town = np.where(df.S2.eq("Nagpur"), "Nagpur", "Smaller towns")
g = df.groupby(town).E1.apply(lambda s: (s>=4).mean())
p_town = chi2_contingency(pd.crosstab(town, t2b))[1]
say(f"Nagpur vs smaller towns intent: {g['Nagpur']:.1%} vs {g['Smaller towns']:.1%} "
    f"(chi-square p={p_town:.3f}, {'significant' if p_town < 0.05 else 'not significant'})")
agree = lambda c: (df[c] >= 4).mean()
say(f"Agree charging points are available: {agree('B2'):.1%} | service centre nearby: {agree('B3'):.1%} | "
    f"running cost is a major reason: {agree('B5'):.1%} | worry about battery safety: {agree('B4'):.1%}")
# keyword coding of the open-ended barrier question (free method from the guide)
CODES = {"Service":["service","repair"], "Charging":["charg"], "Price":["price","expensive","cost is high","upfront"],
         "Resale / battery cost":["resale","second-hand","replacement"], "Safety":["fire","safety","aag"], "Range":["range","highway"]}
def code(t):
    t = str(t).lower()
    for k, ws in CODES.items():
        if any(w in t for w in ws): return k
    return "Other"
df["F1_code"] = df.F1.apply(code)
say("Main barrier (open-ended, keyword-coded): " + "; ".join(f"{k} {v:.0%}" for k, v in df.F1_code.value_counts(normalize=True).items()))
seg = df.groupby("segment").agg(n=("E1","size"), intent=("E1", lambda s: (s>=4).mean()))
# Name segments from their attitude profile, not from K-means label numbers (labels can change).
prof = df.groupby("segment")[[f"B{i}" for i in range(1, 9)]].mean()
tech = prof["B7"].idxmax(); skeptic = prof["B4"].idxmax()
names = {s: ("Tech Early Adopter" if s == tech else "Infrastructure Skeptic" if s == skeptic else "Budget Commuter") for s in prof.index}
assert len(set(names.values())) == 3, "segment naming rule is ambiguous; check the profile"
say("Segments (K-means, k=3): " + "; ".join(f"{names[i]} {int(r.n)} ({r.n/len(df):.0%}), intent {r.intent:.0%}" for i, r in seg.iterrows()))
say(f"EMI preferred by {(df.E2=='EMI').mean():.1%}")
open("06_analysis/outputs/results.txt","w",encoding="utf-8").write("\n".join(out))
