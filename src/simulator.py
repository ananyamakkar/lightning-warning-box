import numpy as np
import matplotlib.pyplot as plt


def storm_distance(t, closest_km, speed_kmh, t_closest_min):
    """Distance (km) from the device to the storm centre at time t (minutes)."""
    speed_km_per_min = speed_kmh / 60
    along_track = speed_km_per_min * (t - t_closest_min)
    return np.sqrt(closest_km**2 + along_track**2)


def generate_strikes(closest_km, speed_kmh, t_closest_min,
                     peak_rate=3, duration=120, seed=None):
    """Return arrays of true strike times (min) and distances (km)."""
    rng = np.random.default_rng(seed)
    dt = 0.1
    times, dists = [], []

    for t in np.arange(0, duration, dt):
        rate = peak_rate * np.exp(-0.5 * ((t - t_closest_min) / 25) ** 2)
        n_strikes = rng.poisson(rate * dt)

        for _ in range(n_strikes):
            d = storm_distance(t, closest_km, speed_kmh, t_closest_min)
            d += rng.normal(0, 2)
            if 1 < d <= 40:
                times.append(t)
                dists.append(d)

    return np.array(times), np.array(dists)


def sensor_observe(times, dists, miss_prob=0.2, false_rate=0.05,
                   duration=120, seed=None):
    """Turn true strikes into what a noisy sensor would report.

    miss_prob: chance the sensor misses a real strike
    false_rate: false triggers per minute (interference)
    """
    rng = np.random.default_rng(seed)

    # 1. Missed strikes
    keep = rng.random(len(times)) > miss_prob
    times, dists = times[keep], dists[keep]

    # 2. Distance error that grows with distance (about 10% of the distance)
    dists = dists + rng.normal(0, 1, len(dists)) * (0.1 * dists)
    dists = np.clip(dists, 1, 40)

    # 3. False triggers at random times and distances
    n_false = rng.poisson(false_rate * duration)
    false_t = rng.uniform(0, duration, n_false)
    false_d = rng.uniform(1, 40, n_false)

    all_t = np.concatenate([times, false_t])
    all_d = np.concatenate([dists, false_d])
    order = np.argsort(all_t)
    is_false = np.concatenate([np.zeros(len(times), bool),
                               np.ones(n_false, bool)])[order]

    return all_t[order], all_d[order], is_false


def random_storm(seed):
    """Make one storm with randomly chosen properties."""
    rng = np.random.default_rng(seed)
    params = {
        "closest_km": rng.uniform(1, 15),
        "speed_kmh": rng.uniform(10, 60),
        "t_closest_min": rng.uniform(40, 80),
        "peak_rate": rng.uniform(0.5, 5),
    }
    times, dists = generate_strikes(**params, seed=seed)
    return params, times, dists


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)

    for i, ax in enumerate(axes):
        params, true_t, true_d = random_storm(seed=i)
        obs_t, obs_d, is_false = sensor_observe(true_t, true_d, seed=i)

        t = np.linspace(0, 120, 300)
        ax.plot(t, storm_distance(t, params["closest_km"],
                                  params["speed_kmh"],
                                  params["t_closest_min"]),
                label="Storm centre")
        ax.scatter(obs_t[~is_false], obs_d[~is_false], s=8, color="red",
                   label="Sensor reports")
        ax.scatter(obs_t[is_false], obs_d[is_false], s=30, color="black",
                   marker="x", label="False triggers")
        ax.set_title(f"Storm {i}: {len(true_t)} true, "
                     f"{len(obs_t)} reported")

    axes[0].legend()
    fig.supxlabel("Time (minutes)")
    fig.supylabel("Distance (km)")
    plt.tight_layout()
    plt.show()