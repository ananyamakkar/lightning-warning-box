import numpy as np
import matplotlib.pyplot as plt
from simulator import storm_distance, sensor_observe, random_storm


def generate_bursty_strikes(closest_km, speed_kmh, t_closest_min,
                            peak_rate=3, duration=120, seed=None,
                            mean_active=6, mean_quiet=8, quiet_level=0.05):
    """Like generate_strikes, but the storm switches between active and quiet spells.

    mean_active / mean_quiet: average length (min) of each spell
    quiet_level: strike rate during a quiet spell, relative to the average
    """
    rng = np.random.default_rng(seed)
    dt = 0.1
    times, dists = [], []

    # Scale the active-spell rate so the long-run average rate stays the same
    p_active = mean_active / (mean_active + mean_quiet)
    active_level = (1 - (1 - p_active) * quiet_level) / p_active

    active = rng.random() < p_active
    for t in np.arange(0, duration, dt):
        # Possibly switch spell
        mean_len = mean_active if active else mean_quiet
        if rng.random() < dt / mean_len:
            active = not active

        envelope = peak_rate * np.exp(-0.5 * ((t - t_closest_min) / 25) ** 2)
        level = active_level if active else quiet_level
        n_strikes = rng.poisson(envelope * level * dt)

        for _ in range(n_strikes):
            d = storm_distance(t, closest_km, speed_kmh, t_closest_min)
            d += rng.normal(0, 2)
            if 1 < d <= 40:
                times.append(t)
                dists.append(d)

    return np.array(times), np.array(dists)


def random_storm_bursty(seed):
    """Same storm path and parameters as random_storm(seed), but bursty strikes."""
    rng = np.random.default_rng(seed)
    params = {
        "closest_km": rng.uniform(1, 15),
        "speed_kmh": rng.uniform(10, 60),
        "t_closest_min": rng.uniform(40, 80),
        "peak_rate": rng.uniform(0.5, 5),
    }
    times, dists = generate_bursty_strikes(**params, seed=seed + 1000)
    return params, times, dists


if __name__ == "__main__":
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharex=True, sharey=True)

    for i in range(3):
        params, st, sd = random_storm(i)
        _, bt, bd = random_storm_bursty(i)
        t = np.linspace(0, 120, 300)
        curve = storm_distance(t, params["closest_km"], params["speed_kmh"],
                               params["t_closest_min"])

        axes[0, i].plot(t, curve)
        axes[0, i].scatter(st, sd, s=6, color="red")
        axes[0, i].set_title(f"Smooth storm {i}: {len(st)} strikes")

        axes[1, i].plot(t, curve)
        axes[1, i].scatter(bt, bd, s=6, color="red")
        axes[1, i].set_title(f"Bursty storm {i}: {len(bt)} strikes")

    fig.supxlabel("Time (minutes)")
    fig.supylabel("Distance (km)")
    plt.tight_layout()
    plt.show()