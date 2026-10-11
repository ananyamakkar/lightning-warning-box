import numpy as np
from simulator import random_storm, sensor_observe

THREAT_KM = 16  # about 10 miles, the distance used in the standard 30-minute rule


def wait_fixed(close_t):
    """The standard rule: always wait 30 minutes after the last close strike."""
    return 30.0


def wait_adaptive(close_t, k=6, min_wait=5, max_wait=30):
    """Wait based on how often strikes have been arriving in this storm."""
    if len(close_t) < 4:
        return max_wait  # not enough history, so be cautious
    gaps = np.diff(close_t[-10:])
    return float(np.clip(k * gaps.mean(), min_wait, max_wait))


def allclear_time(obs_t, obs_d, wait_rule):
    """Time (min) the device first declares all-clear.

    Returns None if the sensor never reported a close strike.
    """
    close_t = obs_t[obs_d <= THREAT_KM]
    if len(close_t) == 0:
        return None
    for i in range(len(close_t)):
        clear = close_t[i] + wait_rule(close_t[:i + 1])
        if i == len(close_t) - 1 or close_t[i + 1] > clear:
            return clear


if __name__ == "__main__":
    print("storm | last danger | fixed clear | fixed unsafe | "
          "adaptive clear | adaptive unsafe")
    for seed in range(12):
        params, true_t, true_d = random_storm(seed)
        obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=seed)
        fixed = allclear_time(obs_t, obs_d, wait_fixed)
        adaptive = allclear_time(obs_t, obs_d, wait_adaptive)
        danger_t = true_t[true_d <= THREAT_KM]

        if len(danger_t) == 0 or fixed is None:
            print(f"{seed:>5} | never threatened")
            continue

        last = danger_t.max()
        fixed_unsafe = "YES" if (danger_t > fixed).any() else "no"
        adaptive_unsafe = "YES" if (danger_t > adaptive).any() else "no"
        print(f"{seed:>5} | {last:>11.1f} | {fixed:>11.1f} | "
              f"{fixed_unsafe:>12} | {adaptive:>14.1f} | {adaptive_unsafe:>15}")