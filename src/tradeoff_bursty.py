import numpy as np
import matplotlib.pyplot as plt
from simulator import random_storm, sensor_observe
from bursty import random_storm_bursty
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time

N_STORMS = 200
k_values = [2, 4, 6, 8, 10, 12, 15, 20]


def build_storms(storm_fn):
    """Generate storms and keep the ones that actually threatened."""
    storms = []
    for seed in range(N_STORMS):
        params, true_t, true_d = storm_fn(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        danger_t = true_t[true_d <= THREAT_KM]
        fixed = allclear_time(obs_t, obs_d, wait_fixed)
        if len(danger_t) > 0 and fixed is not None:
            storms.append((obs_t, obs_d, danger_t, fixed))
    return storms


def run(storms):
    fixed_unsafe = np.mean([(d > f).any() for _, _, d, f in storms]) * 100
    results = []
    for k in k_values:
        unsafe, saved = [], []
        for obs_t, obs_d, danger_t, fixed in storms:
            rule = lambda c, k=k: wait_adaptive(c, k=k)
            clear = allclear_time(obs_t, obs_d, rule)
            unsafe.append((danger_t > clear).any())
            saved.append(fixed - clear)
        results.append((k, np.mean(unsafe) * 100, np.mean(saved)))
    return fixed_unsafe, results


smooth = build_storms(random_storm)
bursty = build_storms(random_storm_bursty)
print(f"Threatening storms: {len(smooth)} smooth, {len(bursty)} bursty")

plt.figure(figsize=(8, 6))
for name, storms, color in [("smooth", smooth, "tab:blue"),
                            ("bursty", bursty, "tab:orange")]:
    fixed_unsafe, results = run(storms)
    print(f"\n{name}: fixed 30-min rule is unsafe in {fixed_unsafe:.1f}% of storms")
    for k, u, s in results:
        print(f"  k={k:>2}: unsafe {u:5.1f}%, saves {s:5.1f} min")
    plt.plot([r[1] for r in results], [r[2] for r in results], "o-",
             color=color, label=f"Adaptive rule, {name} storms")
    plt.scatter([fixed_unsafe], [0], color=color, marker="s", s=80,
                label=f"Fixed 30-min rule, {name}")

plt.xlabel("Storms where a dangerous strike came after all-clear (%)")
plt.ylabel("Average minutes saved vs fixed rule")
plt.title("All-clear tradeoff: smooth vs bursty storms")
plt.legend()
plt.savefig("tradeoff_bursty.png", dpi=150)
plt.show()