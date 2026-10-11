import numpy as np
import matplotlib.pyplot as plt
from simulator import random_storm, sensor_observe
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time

N_STORMS = 200
k_values = [1, 2, 3, 4, 6, 8, 10, 15, 20]

# Pre-generate storms once so every rule is tested on the same data
storms = []
for seed in range(N_STORMS):
    params, true_t, true_d = random_storm(seed)
    obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
    danger_t = true_t[true_d <= THREAT_KM]
    fixed = allclear_time(obs_t, obs_d, wait_fixed)
    if len(danger_t) > 0 and fixed is not None:
        storms.append((obs_t, obs_d, danger_t, fixed))

print(f"{len(storms)} storms were actually threatening")

# Baseline: fixed rule
fixed_unsafe = np.mean([(d > f).any() for _, _, d, f in storms]) * 100
print(f"Fixed 30-min rule: {fixed_unsafe:.1f}% unsafe")

results = []
for k in k_values:
    unsafe, saved = [], []
    for obs_t, obs_d, danger_t, fixed in storms:
        rule = lambda c, k=k: wait_adaptive(c, k=k)
        clear = allclear_time(obs_t, obs_d, rule)
        unsafe.append((danger_t > clear).any())
        saved.append(fixed - clear)
    results.append((k, np.mean(unsafe) * 100, np.mean(saved)))
    print(f"k={k:>2}: unsafe {results[-1][1]:5.1f}%, "
          f"saves {results[-1][2]:5.1f} min on average")

plt.plot([r[1] for r in results], [r[2] for r in results], "o-")
for k, u, s in results:
    plt.annotate(f"k={k}", (u, s), textcoords="offset points", xytext=(5, 5))
plt.scatter([fixed_unsafe], [0], color="red", zorder=5,
            label="Fixed 30-min rule")
plt.xlabel("Storms where a dangerous strike came after all-clear (%)")
plt.ylabel("Average minutes saved vs fixed rule")
plt.title("Adaptive all-clear: safety vs waiting time")
plt.legend()
plt.savefig("tradeoff.png", dpi=150)
plt.show()