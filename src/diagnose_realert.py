import numpy as np
from collections import Counter
from simulator import random_storm, sensor_observe
from allclear import THREAT_KM, wait_fixed, allclear_time
from alert import run_alerts

minutes = list(range(0, 150))
counts = Counter()
total = 0

for seed in range(200):
    params, true_t, true_d = random_storm(seed)
    obs_t, obs_d, is_false = sensor_observe(true_t, true_d, seed=seed)
    danger_t = true_t[true_d <= THREAT_KM]
    fixed = allclear_time(obs_t, obs_d, wait_fixed)
    if len(danger_t) == 0 or fixed is None:
        continue

    first_close = obs_t[obs_d <= THREAT_KM].min()
    states = run_alerts(obs_t, obs_d, minutes)
    greens = [m for m, s in zip(minutes, states)
              if m >= first_close and s == "GREEN"]
    if not greens:
        continue
    total += 1
    g = greens[0]

    later = [(m, s) for m, s in zip(minutes, states) if m > g and s != "GREEN"]
    if not later:
        counts["no re-alert"] += 1
        continue

    m, s = later[0]
    # close strikes heard between the first GREEN and the re-alert
    new = (obs_t > g) & (obs_t <= m) & (obs_d <= THREAT_KM)
    if not new.any():
        kind = "no new close strike"
    elif is_false[new].all():
        kind = "FALSE trigger"
    else:
        kind = "real strike"
    counts[f"{s} caused by {kind}"] += 1

print(f"{total} storms checked")
for name, n in counts.most_common():
    print(f"{n:>4}  {name}")