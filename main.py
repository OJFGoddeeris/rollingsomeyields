import pandas as pd
import numpy as np
from pathlib import Path

ESTR = 2.44  # €STR in %, from Bloomberg
TENORS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30]
VOL_BPS = {}  # annual yield vol per (country, tenor), filled from history tomorrow

df = pd.read_excel("data/Yields_GE_FR_IT_230926.xlsx")
df.columns = ["country", "tenor", "ytm", "zero"]


def screen(df, rate_col):
    """Carry and roll-down screen on one rate column ('zero' or 'ytm')."""
    rows = []
    for country, g in df.groupby("country"):
        for T in TENORS:
            z_T = np.interp(T, g["tenor"], g[rate_col])
            z_prev = np.interp(T - 1, g["tenor"], g[rate_col])
            duration = (T - 1) / (1 + z_prev / 100)
            carry = z_T - ESTR
            roll = (z_T - z_prev) * 100
            excess = carry + duration * (z_T - z_prev)
            breakeven = excess / duration * 100
            vol = VOL_BPS.get((country, T), np.nan)
            rows.append({"country": country, "tenor": T,
                         "carry": round(carry, 2),
                         "rolldown_bps": round(roll, 1),
                         "excess": round(excess, 2),
                         "breakeven_bps": round(breakeven, 1),
                         "vol_bps": vol,
                         "sharpe": round(breakeven / vol, 2),
                         "passes": carry > 0 and roll >= 5})  # positive carry, genuine slope
    return pd.DataFrame(rows)


zero_res = screen(df, "zero")
ytm_res = screen(df, "ytm")

# Put the two side by side
cols = ["country", "tenor", "rolldown_bps", "breakeven_bps", "passes"]
compare = zero_res[cols].merge(ytm_res[cols], on=["country", "tenor"],
                               suffixes=("_zero", "_ytm"))
compare["breakeven_diff"] = (compare["breakeven_bps_ytm"]
                             - compare["breakeven_bps_zero"]).round(1)

pd.set_option("display.width", 200)
print(compare)
print("\nTenors where the two methods disagree on the filter:")
print(compare[compare["passes_zero"] != compare["passes_ytm"]])

# Export
screened = zero_res[zero_res["passes"]].sort_values("sharpe", ascending=False)
Path("output").mkdir(exist_ok=True)
with pd.ExcelWriter("output/ranking.xlsx") as xl:
    screened.to_excel(xl, sheet_name="Ranking", index=False)
    compare.to_excel(xl, sheet_name="Zero vs YTM", index=False)