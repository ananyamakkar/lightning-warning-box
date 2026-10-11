import numpy as np
import matplotlib.pyplot as plt
from simulator import random_storm, sensor_observe
from bursty import random_storm_bursty
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time

N_STORMS = 200


def wait_maxgap(close_t, m=1.5, min_wait=5, max_wait=30):
    """Wait m x the longest gap seen so far in this storm (capped at 30 min)."""
    if len(close_t) < 4:
        return max_wait
    longest = np.diff(close_t).max()
    return float(np.clip(m * longest, min_wait, max_wait))


def build_storms(storm_fn):
    storms = []
    for seed in range(N_STORMS):
        params, true_t, true_d = storm_fn(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        danger_t = true_t[true_d <= THREAT_KM]
        fixed = allclear_time(obs_t, obs_d, wait_fixed)
        if len(danger_t) > 0 and fixed is not None:
            storms.append((obs_t, obs_d, danger_t, fixed))
    return storms


def evaluate(storms, rule):
    unsafe, saved = [], []
    for obs_t, obs_d, danger_t, fixed in storms:
        clear = allclear_time(obs_t, obs_d, rule)
        unsafe.append((danger_t > clear).any())
        saved.append(fixed - clear)
    return np.mean(unsafe) * 100, np.mean(saved)


rules = {}
for k in [6, 12, 20]:
    rules[f"mean-gap k={k}"] = lambda c, k=k: wait_adaptive(c, k=k)
for m in [0.5, 1, 1.5, 2, 3]:
    rules[f"max-gap m={m}"] = lambda c, m=m: wait_maxgap(c, m=m)

datasets = {"smooth": build_storms(random_storm),
            "bursty": build_storms(random_storm_bursty)}

plt.figure(figsize=(8, 6))
for name, storms in datasets.items():
    fixed_unsafe = np.mean([(d > f).any() for _, _, d, f in storms]) * 100
    print(f"\n{name}: {len(storms)} storms, fixed rule unsafe {fixed_unsafe:.1f}%")
    mean_pts, max_pts = [], []
    for label, rule in rules.items():
        u, s = evaluate(storms, rule)
        print(f"  {label:>16}: unsafe {u:5.1f}%, saves {s:5.1f} min")
        (mean_pts if label.startswith("mean") else max_pts).append((u, s))
    ls = "-" if name == "smooth" else "--"
    plt.plot([p[0] for p in mean_pts], [p[1] for p in mean_pts], "o" + ls,
             label=f"mean-gap rule, {name}")
    plt.plot([p[0] for p in max_pts], [p[1] for p in max_pts], "s" + ls,
             label=f"max-gap rule, {name}")
    plt.scatter([fixed_unsafe], [0], marker="*", s=150,
                label=f"fixed 30-min, {name}")

plt.xlabel("Storms where a dangerous strike came after all-clear (%)")
plt.ylabel("Average minutes saved vs fixed rule")
plt.title("All-clear rules: smooth vs bursty storms")
plt.legend(fontsize=8)
plt.savefig("tradeoff_v2.png", dpi=150)
plt.show()