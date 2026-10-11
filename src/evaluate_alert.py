import numpy as np
from simulator import random_storm, sensor_observe
from allclear import THREAT_KM, wait_fixed, wait_adaptive, allclear_time
from alert import run_alerts, K

N_STORMS = 200
minutes = list(range(0, 150))
adaptive_rule = lambda c: wait_adaptive(c, k=K)

n_used = 0
capped = 0      # never reached GREEN before the simulation ended
re_alert = 0    # went back on alert after the first GREEN
unsafe = {"fixed": 0, "adaptive only": 0, "full alert": 0}
saved = {"adaptive only": [], "full alert": []}

for seed in range(N_STORMS):
    params, true_t, true_d = random_storm(seed)
    obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
    danger_t = true_t[true_d <= THREAT_KM]
    fixed = allclear_time(obs_t, obs_d, wait_fixed)
    if len(danger_t) == 0 or fixed is None:
        continue

    # First GREEN once the first close strike has been heard
    first_close = obs_t[obs_d <= THREAT_KM].min()
    states = run_alerts(obs_t, obs_d, minutes)
    greens = [m for m, s in zip(minutes, states)
              if m >= first_close and s == "GREEN"]
    if greens:
        green_start = greens[0]
    else:
        green_start = minutes[-1] + 1
        capped += 1

    if any(s != "GREEN" for m, s in zip(minutes, states) if m > green_start):
        re_alert += 1

    adaptive = allclear_time(obs_t, obs_d, adaptive_rule)
    last_danger = danger_t.max()

    n_used += 1
    unsafe["fixed"] += last_danger > fixed
    unsafe["adaptive only"] += last_danger > adaptive
    unsafe["full alert"] += last_danger > green_start
    saved["adaptive only"].append(fixed - adaptive)
    saved["full alert"].append(fixed - green_start)

print(f"{n_used} threatening storms evaluated")
print(f"Never reached GREEN before the cutoff: {capped}")
print(f"Went back on alert after the first GREEN: {re_alert}")
for name in unsafe:
    print(f"{name:>14}: {100 * unsafe[name] / n_used:5.1f}% unsafe")
for name, s in saved.items():
    s = np.array(s)
    print(f"{name:>14}: saves mean {s.mean():5.1f}, median {np.median(s):5.1f}, "
          f"10th pct {np.percentile(s, 10):6.1f}, 90th pct {np.percentile(s, 90):5.1f} min")