import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from pathlib import Path

OUT = Path("06_analysis/outputs"); OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv("05_qc/survey_clean.csv")
ATT = [f"B{i}" for i in range(1, 9)]
df["intent_t2b"] = (df["E1"] >= 4).map({True: "Likely", False: "Not likely"})
df["town"] = np.where(df["S2"].eq("Nagpur"), "Nagpur", "Smaller towns")

# ---------- A. Crosstabs with significance ----------
def crosstab_test(col):
    ct = pd.crosstab(df[col], df["intent_t2b"])
    chi2, p, dof, expected = chi2_contingency(ct)
    pct = pd.crosstab(df[col], df["intent_t2b"], normalize="index").mul(100).round(1)
    ok = (expected >= 5).mean() >= 0.8
    print(f"{col}: p={p:.3f} {'SIGNIFICANT' if p < 0.05 else 'not significant'}"
          f"{'' if ok else '  (low expected counts: merge groups)'}")
    return pct.assign(n=ct.sum(axis=1), p_value=round(p, 3))

with pd.ExcelWriter(OUT / "crosstabs.xlsx") as xw:
    for col in ["S1", "town", "C2", "S3", "G2"]:
        crosstab_test(col).to_excel(xw, sheet_name=col)

# ---------- B. Segmentation ----------
X = StandardScaler().fit_transform(df[ATT])
scores = {k: silhouette_score(X, KMeans(k, n_init=20, random_state=42).fit_predict(X))
          for k in range(2, 7)}
print("Silhouette by k:", {k: round(v, 3) for k, v in scores.items()})
K = 3   # pick using silhouette + whether segments make business sense
df["segment"] = KMeans(K, n_init=20, random_state=42).fit_predict(X)
profile = df.groupby("segment").agg(
    size=("resp_id", "count"), intent_t2b=("E1", lambda s: (s >= 4).mean()),
    **{c: (c, "mean") for c in ATT}).round(2)
profile.to_csv(OUT / "segment_profile.csv")
print(profile)
# Look at the means and NAME them, e.g. "Budget Commuter", "Tech Early Adopter",
# "Infrastructure Skeptic". Then map: df["persona"] = df["segment"].map({...})
df.to_csv(OUT / "survey_with_segments.csv", index=False)

# ---------- C. Van Westendorp ----------
p = df[df["price_valid"]]
grid = np.arange(p[["D1","D2","D3","D4"]].min().min(), p[["D1","D2","D3","D4"]].max().max(), 1000)
too_cheap = np.array([(p["D1"] >= x).mean() for x in grid])
cheap     = np.array([(p["D2"] >= x).mean() for x in grid])
expensive = np.array([(p["D3"] <= x).mean() for x in grid])
too_exp   = np.array([(p["D4"] <= x).mean() for x in grid])
cross = lambda a, b: grid[np.argmin(np.abs(a - b))]
res = {
    "PMC (lower bound)": cross(too_cheap, 1 - cheap),
    "OPP (optimal)":     cross(too_cheap, too_exp),
    "IPP (indifference)":cross(cheap, expensive),
    "PME (upper bound)": cross(too_exp, 1 - expensive),
}
print({k: f"₹{v:,.0f}" for k, v in res.items()}, f"n={len(p)}")
plt.figure(figsize=(9, 5))
for y, lab in [(too_cheap,"Too cheap"),(1-cheap,"Not a bargain"),(1-expensive,"Not expensive"),(too_exp,"Too expensive")]:
    plt.plot(grid, y, label=lab)
plt.axvspan(res["PMC (lower bound)"], res["PME (upper bound)"], alpha=.12)
plt.xlabel("Price (₹)"); plt.ylabel("Share of respondents"); plt.legend()
plt.title("Acceptable price range: electric scooter, Tier-2 Vidarbha")
plt.savefig(OUT / "van_westendorp.png", dpi=150, bbox_inches="tight")

# ---------- D. Brand funnel ----------
BRANDS = ["Brand A","Brand B","Brand C","Brand D","Brand E","Brand F"]
n = len(df)
funnel = pd.DataFrame({
    "aware":    [df["A1"].str.contains(b, regex=False, na=False).mean() for b in BRANDS],
    "consider": [df["A2"].str.contains(b, regex=False, na=False).mean() for b in BRANDS],
    "prefer":   [df["A3"].eq(b).mean() for b in BRANDS]}, index=BRANDS)
funnel["aware_to_consider"] = funnel["consider"] / funnel["aware"]
funnel["consider_to_prefer"] = funnel["prefer"] / funnel["consider"]
funnel.round(3).to_csv(OUT / "funnel.csv")
print(funnel.round(2))

# ---------- E. Key drivers of intent ----------
drivers = pd.DataFrame(
    [(c, *spearmanr(df[c], df["E1"])) for c in ATT], columns=["attitude","rho","p"]
).sort_values("rho", key=abs, ascending=False)
drivers.to_csv(OUT / "drivers.csv", index=False)
print(drivers.round(3))