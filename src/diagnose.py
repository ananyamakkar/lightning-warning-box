import numpy as np
from simulator import random_storm, sensor_observe
from countdown import estimate_eta
from allclear import THREAT_KM, wait_fixed, allclear_time
from alert import alert_state, run_alerts

minutes = list(range(0, 150))


def red_reason(obs_t, obs_d, is_false, now):
    """Why the raw alert logic says RED at this minute."""
    seen = obs_t <= now
    t, d, f = obs_t[seen], obs_d[seen], is_false[seen]
    recent = (t > now - 5) & (d <= 10)
    if recent.any():
        kind = "FALSE trigger" if f[recent].all() else "real strike"
        return f"close strike in last 5 min ({kind})"
    eta = estimate_eta(t, d, now)
    if eta is not None and eta <= 10:
        return f"countdown estimate {eta:.1f} min"
    return "none"


rows = []
for seed in range(200):
    params, true_t, true_d = random_storm(seed)
    obs_t, obs_d, is_false = sensor_observe(true_t, true_d, seed=seed)
    danger_t = true_t[true_d <= THREAT_KM]
    fixed = allclear_time(obs_t, obs_d, wait_fixed)
    if len(danger_t) == 0 or fixed is None:
        continue
    states = run_alerts(obs_t, obs_d, minutes)
    non_green = [m for m, s in zip(minutes, states) if s != "GREEN"]
    if not non_green:
        continue
    green_start = non_green[-1] + 1
    rows.append((fixed - green_start, seed, green_start, fixed,
                 danger_t.max(), obs_t, obs_d, is_false))

rows.sort(key=lambda r: r[0])  # worst delay first

print("seed | delay vs fixed | real last danger | last RED trigger | why")
for saved, seed, green, fixed, last_danger, obs_t, obs_d, is_false in rows[:8]:
    raw_red = [m for m in minutes
               if alert_state(obs_t, obs_d, m) == "RED"]
    if raw_red:
        m = raw_red[-1]
        why = red_reason(obs_t, obs_d, is_false, m)
    else:
        m, why = -1, "no raw RED"
    print(f"{seed:>4} | {saved:>10.1f} min | {last_danger:>14.1f} | "
          f"{m:>16} | {why}")