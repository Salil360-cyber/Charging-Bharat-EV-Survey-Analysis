"""
Charging Bharat: SIMULATED survey data generator
------------------------------------------------
Creates a realistic, clearly-labelled SIMULATED survey export (Microsoft Forms style)
so the QC and analysis pipeline can be demonstrated. It is NOT real consumer data.
Brands are fictional (Brand A-F). Seeded, so every run gives the same file.
Output: 04_data/raw_responses.xlsx
"""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(2026)
N_GOOD = 380
L = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
BR = ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E", "Brand F"]
AWARE_P = [0.86, 0.71, 0.64, 0.58, 0.39, 0.27]          # fictional awareness levels

# persona -> mean attitude on B1..B8 (1-5 scale)
PERS = {
  "commuter": dict(w=0.45, B=[3.0,2.9,2.8,3.4,4.4,3.8,3.0,3.4], price=95000, intent=0.0),
  "tech":     dict(w=0.22, B=[3.9,3.3,3.2,2.4,3.9,2.8,4.5,2.9], price=120000, intent=1.4),
  "skeptic":  dict(w=0.33, B=[2.3,2.2,2.2,4.2,3.2,4.3,2.4,4.0], price=80000, intent=-1.4),
}
BARRIER = {
  "service":  ["No service centre near Gondia", "Service ka koi option nahi hai yahan", "If it breaks, who will repair it here?", "Service network is weak in small towns"],
  "charging": ["Charging points are not available", "Where will I charge outside the house?", "Charging station nahi hai town mein", "Long trips need charging stops"],
  "price":    ["Too expensive compared to petrol scooter", "Price bahut zyada hai", "Upfront cost is high even with subsidy"],
  "resale":   ["Resale value is uncertain", "Battery replacement cost worries me", "Nobody buys second-hand EVs here"],
  "safety":   ["Battery fire news scares me", "Safety concerns about battery", "EV aag lagne ki news dekhi hai"],
  "range":    ["Range is not enough for my daily travel", "Battery may not last on highway", "Range kam hai"],
}
BARR_W = {"commuter":[.34,.22,.20,.12,.06,.06], "tech":[.30,.30,.14,.08,.06,.12], "skeptic":[.26,.24,.10,.14,.18,.08]}
MOTIV = ["Service centre in my town", "Lower price or better EMI", "Fast charging nearby", "Longer battery warranty", "Better range", "Good resale value guarantee"]

def likert(mu, n=1):
    return np.clip(np.rint(rng.normal(mu, 0.85, n)), 1, 5).astype(int)

start0 = pd.Timestamp("2026-10-05 09:00")
def make_row():
    p = rng.choice(list(PERS), p=[v["w"] for v in PERS.values()]); P = PERS[p]
    town = rng.choice(["Nagpur","Gondia","Bhandara","Chandrapur","Wardha","Other Vidarbha"], p=[.46,.18,.10,.10,.08,.08])
    age = rng.choice(["18–24","25–34","35–44","45+"], p={"commuter":[.20,.42,.26,.12],"tech":[.52,.36,.09,.03],"skeptic":[.14,.26,.30,.30]}[p])
    small = town != "Nagpur"
    B = [int(likert(m)[0]) for m in P["B"]]
    if small:
        B[1] = max(1, B[1]-1); B[2] = max(1, B[2]-1)          # charging/service worse in small towns
    home = rng.choice(["Yes","No","Not sure"], p=[.72,.20,.08] if small else [.52,.38,.10])
    # purchase intent (1-5) from a latent score
    z = P["intent"] + (0.9 if home=="Yes" else -0.5) + 0.25*(B[0]-3) + 0.25*(B[4]-3) - 0.3*(B[3]-3) + 0.2*(B[6]-3) + rng.normal(0, 1.0)
    e1 = int(np.digitize(z, [-1.6, -0.4, 0.6, 1.6]) + 1)
    # prices: round numbers like real respondents
    bargain = rng.normal(P["price"]*0.9, 12000)
    d = [bargain*rng.uniform(.62,.82), bargain, bargain*rng.uniform(1.18,1.38)]
    d.append(d[2]*rng.uniform(1.12,1.30))
    d = [int(round(x/5000)*5000) for x in d]
    if len(set(d)) < 4: d = sorted(set(d)) + [d[-1]+5000*k for k in range(1, 5-len(set(d)))]
    aware = [b for b, pr in zip(BR, AWARE_P) if rng.random() < pr] or ["Brand A"]
    consider = [b for b in aware if rng.random() < (0.55 if e1 >= 4 else 0.25)]
    pref = rng.choice(consider) if consider and e1 >= 3 else "I would buy petrol"
    bk = rng.choice(list(BARRIER), p=BARR_W[p])
    dur = max(160, rng.normal(310, 75))
    st = start0 + pd.Timedelta(minutes=int(rng.integers(0, 60*24*12)))
    return {
        "Start time": st, "Completion time": st + pd.Timedelta(seconds=float(dur)),
        "S1": age, "S2": town,
        "S3": rng.choice(["Yes, petrol","Yes, electric","No"], p=[.66,.06,.28]),
        "S4": rng.choice(["Yes","Maybe","No"], p=[.42,.40,.18]),
        "A1": ";".join(aware), "A2": ";".join(consider), "A3": pref,
        **{f"B{k+1}": L[v-1] for k, v in enumerate(B)}, "B9": "Agree",
        "C1": rng.choice(["<10","10–25","25–50","50+"], p=[.18,.44,.28,.10]), "C2": home,
        "D1": d[0], "D2": d[1], "D3": d[2], "D4": d[3],
        "E1": ["Definitely not","Probably not","Not sure","Probably will","Definitely will"][e1-1],
        "E2": rng.choice(["Full payment","EMI","Not sure"], p=[.28,.55,.17]),
        "F1": rng.choice(BARRIER[bk]), "F2": rng.choice(MOTIV),
        "G1": rng.choice(["Male","Female","Prefer not to say"], p=[.62,.35,.03]),
        "G2": rng.choice(["Student","Salaried","Self-employed","Homemaker","Other"],
                         p={"commuter":[.08,.48,.30,.08,.06],"tech":[.45,.40,.10,.02,.03],"skeptic":[.06,.34,.38,.14,.08]}[p]),
        "G3": rng.choice(["<₹25k","₹25–50k","₹50k–1L","₹1L+","Prefer not to say"], p=[.22,.38,.24,.08,.08]),
        "_persona_truth": p, "_barrier_truth": bk}
df = pd.DataFrame([make_row() for _ in range(N_GOOD)])

# ---- inject realistic bad responses (what QC must catch) ----
bad = []
def clone(k):
    # a NEW respondent with a problem (not a copy of a genuine row)
    r = pd.Series(make_row()); r["_injected"] = k; return r
for _ in range(14):   # speeders
    r = clone("speeder"); r["Completion time"] = r["Start time"] + pd.Timedelta(seconds=int(rng.integers(25, 90))); bad.append(r)
for _ in range(10):   # straight-liners
    r = clone("straight_liner"); v = rng.choice(L)
    for k in range(1, 9): r[f"B{k}"] = v
    r["B9"] = v; bad.append(r)
for _ in range(12):   # failed attention check
    r = clone("attention"); r["B9"] = rng.choice(["Neutral","Disagree","Strongly agree"]); bad.append(r)
for _ in range(6):    # under 18
    r = clone("under_18"); r["S1"] = "Under 18"; bad.append(r)
for _ in range(8):    # outside target area
    r = clone("outside"); r["S2"] = "Outside Vidarbha"; bad.append(r)
for _ in range(4):    # exact duplicate submissions (same person submitting twice)
    r = df.iloc[int(rng.integers(0, len(df)))].copy(); r["_injected"] = "duplicate"; r["Start time"] += pd.Timedelta(hours=2); r["Completion time"] += pd.Timedelta(hours=2); bad.append(r)
for _ in range(6):    # illogical prices (kept, but excluded from pricing)
    j = int(rng.integers(0, len(df))); df.loc[j, ["D3","D4"]] = df.loc[j, ["D4","D3"]].values; df.loc[j, "_injected"] = "price_order"
out = pd.concat([df, pd.DataFrame(bad)], ignore_index=True).sample(frac=1, random_state=7).reset_index(drop=True)
out["_injected"] = out["_injected"].fillna("")
Path("04_data").mkdir(exist_ok=True)
truth = out[["_persona_truth","_barrier_truth","_injected"]]
out.drop(columns=truth.columns).to_excel("04_data/raw_responses.xlsx", index=False)
# (answer key not saved: analysis must not peek at the truth)
print(f"Simulated responses written: {len(out)} ({N_GOOD} genuine + {len(bad)} injected bad rows + 6 price-logic errors)")
