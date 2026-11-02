import pandas as pd
import numpy as np
from pathlib import Path

Path("05_qc").mkdir(exist_ok=True)

df = pd.read_excel("04_data/raw_responses.xlsx")

# 1) Rename long Forms headers to codes. Fill this from your export.
RENAME = {
    "Start time": "start", "Completion time": "end",
    # "Your age?": "S1", "Which city/town do you live in?": "S2", ...
}
df = df.rename(columns=RENAME)
df["resp_id"] = range(1, len(df) + 1)

LIKERT_TEXT = {"Strongly disagree": 1, "Disagree": 2, "Neutral": 3,
               "Agree": 4, "Strongly agree": 5}
ATT = [f"B{i}" for i in range(1, 9)]
for c in ATT + ["B9"]:
    df[c] = df[c].map(LIKERT_TEXT)

INTENT = {"Definitely will": 5, "Probably will": 4, "Not sure": 3,
          "Probably not": 2, "Definitely not": 1}
df["E1"] = df["E1"].map(INTENT)
for c in ["D1", "D2", "D3", "D4"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# 2) Flags
df["duration_sec"] = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.total_seconds()
median_t = df["duration_sec"].median()
df["f_speeder"]    = df["duration_sec"] < median_t / 3
df["f_straight"]   = df[ATT].std(axis=1) == 0
df["f_attention"]  = df["B9"] != 4
df["f_underage"]   = df["S1"].eq("Under 18")
df["f_outside"]    = df["S2"].eq("Outside Vidarbha")
df["f_price_order"] = ~((df["D1"] < df["D2"]) & (df["D2"] < df["D3"]) & (df["D3"] < df["D4"]))
df["f_price_range"] = (df[["D1","D2","D3","D4"]].lt(10_000) | df[["D1","D2","D3","D4"]].gt(500_000)).any(axis=1)
answer_cols = [c for c in df.columns if c[:1] in "SABCDEG" and c[1:].isdigit()]
df["f_duplicate"]  = df.duplicated(subset=answer_cols, keep="first")

# Hard fails remove the response. Price-only fails keep the response
# but exclude it from the pricing analysis.
hard = ["f_speeder","f_straight","f_attention","f_underage","f_outside","f_duplicate"]
df["remove"] = df[hard].any(axis=1)
df["price_valid"] = ~(df["f_price_order"] | df["f_price_range"])

log = df.loc[df["remove"] | ~df["price_valid"], ["resp_id","duration_sec"] + hard + ["f_price_order","f_price_range"]]
with pd.ExcelWriter("05_qc/qc_log.xlsx") as xw:
    log.to_excel(xw, sheet_name="flagged", index=False)
    pd.DataFrame({
        "metric": ["received", "removed", "clean", "price_valid (of clean)"] + hard,
        "count":  [len(df), df["remove"].sum(), (~df["remove"]).sum(),
                   df.loc[~df["remove"], "price_valid"].sum()] + [df[f].sum() for f in hard],
    }).to_excel(xw, sheet_name="summary", index=False)

clean = df[~df["remove"]].drop(columns=hard + ["remove"])
clean.to_csv("05_qc/survey_clean.csv", index=False)
print(f"Received {len(df)}, clean {len(clean)}, price-valid {clean['price_valid'].sum()}")