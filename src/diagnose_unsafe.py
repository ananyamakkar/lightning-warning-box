import numpy as np
from simulator import random_storm, sensor_observe
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time
from alert import K

N_STORMS = 200
rules = {
    "fixed 30-min": wait_fixed,
    f"adaptive k={K}": lambda c: wait_adaptive(c, k=K),
}

n_no_danger = 0       # storm never had a real strike within THREAT_KM
n_silent = 0          # real danger, but sensor never reported a close strike
n_used = 0
first_close_false = 0  # first reported close strike was a false trigger
counts = {name: {"safe": 0, "cleared before storm": 0, "cleared mid-storm": 0}
          for name in rules}

for seed in range(N_STORMS):
    params, true_t, true_d = random_storm(seed)
    obs_t, obs_d, is_false = sensor_observe(true_t, true_d, seed=seed)
    danger_t = true_t[true_d <= THREAT_KM]
    fixed = allclear_time(obs_t, obs_d, wait_fixed)

    if len(danger_t) == 0:
        n_no_danger += 1
        continue
    if fixed is None:
        n_silent += 1
        continue

    n_used += 1
    first_danger = danger_t.min()
    if is_false[obs_d <= THREAT_KM][0]:
        first_close_false += 1

    for name, rule in rules.items():
        clear = allclear_time(obs_t, obs_d, rule)
        if not (danger_t > clear).any():
            counts[name]["safe"] += 1
        elif clear < first_danger:
            counts[name]["cleared before storm"] += 1
        else:
            counts[name]["cleared mid-storm"] += 1

print(f"{N_STORMS} storms: {n_no_danger} never dangerous, "
      f"{n_silent} dangerous but sensor heard no close strike, "
      f"{n_used} evaluated")
print(f"Storms where the first reported close strike was a false trigger: "
      f"{first_close_false}")
for name, c in counts.items():
    print(f"\n{name}:")
    for kind, n in c.items():
        print(f"  {kind:>22}: {n:>3}  ({100 * n / n_used:4.1f}%)")