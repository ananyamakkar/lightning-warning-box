import numpy as np
import matplotlib.pyplot as plt
from simulator import random_storm, sensor_observe
from countdown import estimate_eta, true_arrival

lead_times = [30, 20, 10, 5]  # minutes before the storm really arrives
errors = {L: [] for L in lead_times}
no_estimate = {L: 0 for L in lead_times}

for seed in range(100):
    params, true_t, true_d = random_storm(seed)
    arrival = true_arrival(params)
    if arrival is None:
        continue  # storm never gets within 10 km
    obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)

    for L in lead_times:
        now = arrival - L
        if now < 0:
            continue  # storm was already close when the simulation began
        est = estimate_eta(obs_t, obs_d, now)
        if est is None:
            no_estimate[L] += 1
        else:
            errors[L].append(est - L)  # negative = estimate too short

print("Lead time | storms | no estimate | median error | median abs error")
for L in lead_times:
    e = np.array(errors[L])
    n = len(e) + no_estimate[L]
    if len(e) > 0:
        print(f"{L:>6} min | {n:>6} | {no_estimate[L]:>11} | "
              f"{np.median(e):>9.1f} min | {np.median(np.abs(e)):>10.1f} min")
    else:
        print(f"{L:>6} min | {n:>6} | {no_estimate[L]:>11} | no data")

plt.boxplot([errors[L] for L in lead_times])
plt.xticks(range(1, len(lead_times) + 1),
           [f"{L} min before" for L in lead_times])
plt.axhline(0, color="gray", linestyle="--")
plt.ylabel("Estimate minus true time (minutes)")
plt.title("Countdown error across simulated storms")
plt.show()