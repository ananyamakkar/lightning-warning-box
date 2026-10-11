import numpy as np
from simulator import random_storm, sensor_observe
from countdown import estimate_eta
from allclear import THREAT_KM, wait_adaptive, wait_fixed, allclear_time

K = 12  # all-clear caution setting (between k=10 and k=15 in our results)
RED_HOLD_MIN = 10  # once RED, stay RED at least this long


def is_receding(t, d, now):
    """True if strikes in the last 10 min are clearly farther than the 10 min before."""
    recent = d[t > now - 10]
    earlier = d[(t > now - 20) & (t <= now - 10)]
    return (len(recent) >= 3 and len(earlier) >= 3
            and recent.mean() > earlier.mean() + 2)


def alert_state(obs_t, obs_d, now):
    """Return "GREEN", "YELLOW" or "RED" using only strikes up to `now`."""
    seen = obs_t <= now
    t, d = obs_t[seen], obs_d[seen]
    if len(t) == 0:
        return "GREEN"

    # RED: two strikes within 10 km in the last 5 minutes (one could be false)
    if ((t > now - 5) & (d <= 10)).sum() >= 2:
        return "RED"

    # RED: countdown says arrival within 10 min, unless the storm is moving away
    eta = estimate_eta(t, d, now)
    if eta is not None and eta <= 10 and not is_receding(t, d, now):
        return "RED"

    close_t = t[d <= THREAT_KM]

    if len(close_t) > 0:
        # Storm has been close: the adaptive all-clear rule decides when to relax
        if now < close_t[-1] + wait_adaptive(close_t, k=K):
            return "YELLOW"
    else:
        # Storm hasn't been close yet: early heads-up if strikes within 30 km
        if ((t > now - 10) & (d <= 30)).any():
            return "YELLOW"

    return "GREEN"


def run_alerts(obs_t, obs_d, minutes, hold=RED_HOLD_MIN):
    """Run alert_state over time, holding RED for at least `hold` minutes."""
    states = []
    prev = None
    red_start = None
    for now in minutes:
        s = alert_state(obs_t, obs_d, now)
        if prev == "RED" and s != "RED" and now - red_start < hold:
            s = "RED"
        if s == "RED" and prev != "RED":
            red_start = now
        states.append(s)
        prev = s
    return states


if __name__ == "__main__":
    params, true_t, true_d = random_storm(seed=1)
    obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=1)

    minutes = list(range(0, 150))
    states = run_alerts(obs_t, obs_d, minutes)

    last = None
    for now, state in zip(minutes, states):
        if state != last:
            print(f"minute {now:>3}: {state}")
            last = state

    fixed = allclear_time(obs_t, obs_d, wait_fixed)
    print(f"Fixed 30-min rule would clear at minute {fixed:.1f}")