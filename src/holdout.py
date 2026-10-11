import numpy as np
from simulator import random_storm, sensor_observe
from bursty import random_storm_bursty
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time

SEEDS = range(1000, 1500)  # fresh storms, never used while tuning


def wait_maxgap(close_t, m=3, min_wait=5, max_wait=30):
    if len(close_t) < 4:
        return max_wait
    longest = np.diff(close_t).max()
    return float(np.clip(m * longest, min_wait, max_wait))


def wait_path(t_hist, d_hist, margin_km=22, min_wait=5, max_wait=30, window=20):
    now = t_hist[-1]
    keep = t_hist > now - window
    t, d = t_hist[keep], d_hist[keep]
    if len(t) < 6:
        return max_wait
    slope, icpt = np.polyfit(t, d, 1)
    resid = d - (slope * t + icpt)
    ok = np.abs(resid) < 2 * resid.std()
    if ok.sum() >= 4:
        slope, icpt = np.polyfit(t[ok], d[ok], 1)
    if slope < 0.05:
        return max_wait
    current = slope * now + icpt
    if current >= margin_km:
        return min_wait
    return float(np.clip((margin_km - current) / slope, min_wait, max_wait))


def allclear_path(obs_t, obs_d, wait_fn):
    close_idx = np.where(obs_d <= THREAT_KM)[0]
    if len(close_idx) == 0:
        return None
    for j, idx in enumerate(close_idx):
        clear = obs_t[idx] + wait_fn(obs_t[:idx + 1], obs_d[:idx + 1])
        if j == len(close_idx) - 1 or obs_t[close_idx[j + 1]] > clear:
            return clear


rules = {
    "fixed 30-min": lambda t, d: allclear_time(t, d, wait_fixed),
    "mean-gap k=12": lambda t, d: allclear_time(t, d, lambda c: wait_adaptive(c, k=12)),
    "max-gap m=3": lambda t, d: allclear_time(t, d, lambda c: wait_maxgap(c, m=3)),
    "path margin=22": lambda t, d: allclear_path(t, d, lambda a, b: wait_path(a, b, margin_km=22)),
    "path margin=26": lambda t, d: allclear_path(t, d, lambda a, b: wait_path(a, b, margin_km=26)),
}

for label, storm_fn in [("smooth", random_storm), ("bursty", random_storm_bursty)]:
    storms = []
    for seed in SEEDS:
        params, true_t, true_d = storm_fn(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        danger_t = true_t[true_d <= THREAT_KM]
        if len(danger_t) > 0 and (obs_d <= THREAT_KM).any():
            storms.append((obs_t, obs_d, danger_t))

    n = len(storms)
    print("")
    print("=== " + label + " storms: " + str(n) + " fresh storms evaluated ===")
    fixed_clears = [rules["fixed 30-min"](t, d) for t, d, _ in storms]

    for name, rule in rules.items():
        unsafe, mid, saved = 0, 0, []
        for (t, d, danger_t), fixed in zip(storms, fixed_clears):
            clear = rule(t, d)
            if (danger_t > clear).any():
                unsafe += 1
                if clear >= danger_t.min():
                    mid += 1
            saved.append(fixed - clear)
        print("%15s: unsafe %5.1f%% (mid-storm %4.1f%%), saves %5.1f min"
              % (name, 100 * unsafe / n, 100 * mid / n, np.mean(saved)))