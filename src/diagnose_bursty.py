import numpy as np
from simulator import random_storm, sensor_observe
from bursty import random_storm_bursty
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time

N_STORMS = 200


def wait_maxgap(close_t, m=3, min_wait=5, max_wait=30):
    if len(close_t) < 4:
        return max_wait
    longest = np.diff(close_t).max()
    return float(np.clip(m * longest, min_wait, max_wait))


rules = {
    "fixed 30-min": wait_fixed,
    "mean-gap k=12": lambda c: wait_adaptive(c, k=12),
    "max-gap m=3": lambda c: wait_maxgap(c, m=3),
}

for label, storm_fn in [("smooth", random_storm),
                        ("bursty", random_storm_bursty)]:
    counts = {n: {"safe": 0, "cleared before storm": 0, "cleared mid-storm": 0}
              for n in rules}
    n_used = 0

    for seed in range(N_STORMS):
        params, true_t, true_d = storm_fn(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        danger_t = true_t[true_d <= THREAT_KM]
        fixed = allclear_time(obs_t, obs_d, wait_fixed)
        if len(danger_t) == 0 or fixed is None:
            continue

        n_used += 1
        first_danger = danger_t.min()
        for name, rule in rules.items():
            clear = allclear_time(obs_t, obs_d, rule)
            if not (danger_t > clear).any():
                counts[name]["safe"] += 1
            elif clear < first_danger:
                counts[name]["cleared before storm"] += 1
            else:
                counts[name]["cleared mid-storm"] += 1

    print(f"\n=== {label} storms ({n_used} evaluated) ===")
    for name, c in counts.items():
        print(name)
        for kind, v in c.items():
            print(f"    {kind:>22}: {100 * v / n_used:5.1f}%")