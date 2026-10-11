import numpy as np
from simulator import random_storm, sensor_observe, storm_distance


def estimate_eta(obs_t, obs_d, now, window=20, danger_km=10):
    """Estimate minutes until the storm is within danger_km.

    Uses only strikes from the last `window` minutes.
    Returns None if there isn't enough data or the storm isn't approaching.
    """
    mask = (obs_t <= now) & (obs_t > now - window)
    t, d = obs_t[mask], obs_d[mask]
    if len(t) < 6:
        return None

    # Fit a line, drop points far from it (false triggers), fit again
    slope, intercept = np.polyfit(t, d, 1)
    resid = d - (slope * t + intercept)
    keep = np.abs(resid) < 2 * resid.std()
    if keep.sum() >= 4:
        slope, intercept = np.polyfit(t[keep], d[keep], 1)

    if slope > -0.05:  # not getting closer
        return None

    current = slope * now + intercept
    if current <= danger_km:
        return 0.0
    return (current - danger_km) / (-slope)


def true_arrival(params, danger_km=10):
    """The real time (min) the storm first gets within danger_km.

    Returns None if the storm never gets that close.
    """
    for t in np.arange(0, 120, 0.1):
        d = storm_distance(t, params["closest_km"], params["speed_kmh"],
                           params["t_closest_min"])
        if d <= danger_km:
            return t
    return None


if __name__ == "__main__":
    params, true_t, true_d = random_storm(seed=1)
    obs_t, obs_d, is_false = sensor_observe(true_t, true_d, seed=1)
    arrival = true_arrival(params)

    if arrival is None:
        print("This storm never gets within 10 km. Try a different seed.")
    else:
        print(f"Storm reaches 10 km at minute {arrival:.1f}")
        for now in [15, 20, 25, 30, 35, 40]:
            est = estimate_eta(obs_t, obs_d, now)
            true_eta = arrival - now
            est_text = f"{est:5.1f}" if est is not None else " none"
            print(f"now={now}: estimated {est_text} min, true {true_eta:5.1f} min")