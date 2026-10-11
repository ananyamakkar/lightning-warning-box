import numpy as np
from simulator import random_storm, sensor_observe
from bursty import random_storm_bursty
from allclear import THREAT_KM, wait_fixed, allclear_time

N_STORMS = 200


def wait_path(t_hist, d_hist, margin_km=22, min_wait=5, max_wait=30, window=20):
    """Wait until the fitted storm path says the storm is past margin_km.

    t_hist, d_hist: all strikes the sensor reported up to this moment.
    """
    now = t_hist[-1]
    keep = t_hist > now - window
    t, d = t_hist[keep], d_hist[keep]
    if len(t) < 6:
        return max_wait

    # Fit distance vs time, drop outliers (false triggers), fit again
    slope, icpt = np.polyfit(t, d, 1)
    resid = d - (slope * t + icpt)
    ok = np.abs(resid) < 2 * resid.std()
    if ok.sum() >= 4:
        slope, icpt = np.polyfit(t[ok], d[ok], 1)

    if slope < 0.05:  # not clearly moving away: be cautious
        return max_wait
    current = slope * now + icpt
    if current >= margin_km:
        return min_wait
    return float(np.clip((margin_km - current) / slope, min_wait, max_wait))


def allclear_path(obs_t, obs_d, wait_fn):
    """Same logic as allclear_time, but the rule also sees the strike distances."""
    close_idx = np.where(obs_d <= THREAT_KM)[0]
    if len(close_idx) == 0:
        return None
    for j, idx in enumerate(close_idx):
        clear = obs_t[idx] + wait_fn(obs_t[:idx + 1], obs_d[:idx + 1])
        if j == len(close_idx) - 1 or obs_t[close_idx[j + 1]] > clear:
            return clear


datasets = {"smooth": random_storm, "bursty": random_storm_bursty}
margins = [14, 18, 22, 26, 30]

for name, storm_fn in datasets.items():
    storms = []
    for seed in range(N_STORMS):
        params, true_t, true_d = storm_fn(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        danger_t = true_t[true_d <= THREAT_KM]
        fixed = allclear_time(obs_t, obs_d, wait_fixed)
        if len(danger_t) > 0 and fixed is not None:
            storms.append((obs_t, obs_d, danger_t, fixed))

    fixed_unsafe = np.mean([(d > f).any() for _, _, d, f in storms]) * 100
    print(f"\n{name}: {len(storms)} storms, fixed rule unsafe {fixed_unsafe:.1f}%")

    for margin in margins:
        unsafe, mid, saved = 0, 0, []
        for obs_t, obs_d, danger_t, fixed in storms:
            rule = lambda t, d, m=margin: wait_path(t, d, margin_km=m)
            clear = allclear_path(obs_t, obs_d, rule)
            if (danger_t > clear).any():
                unsafe += 1
                if clear >= danger_t.min():
                    mid += 1
            saved.append(fixed - clear)
        n = len(storms)
        print(f"  margin={margin:>2} km: unsafe {100 * unsafe / n:5.1f}% "
              f"(mid-storm {100 * mid / n:5.1f}%), "
              f"saves {np.mean(saved):5.1f} min")