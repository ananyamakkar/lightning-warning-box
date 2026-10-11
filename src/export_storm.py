from simulator import random_storm, sensor_observe

SEED = 1
params, true_t, true_d = random_storm(SEED)
obs_t, obs_d, _ = sensor_observe(true_t, true_d, seed=SEED)

lines = [
    f"// Storm seed {SEED}: {len(obs_t)} reported strikes (time in min, distance in km)",
    f"const int N_STRIKES = {len(obs_t)};",
    "const float STRIKE_T[] = {" + ", ".join(f"{x:.2f}" for x in obs_t) + "};",
    "const float STRIKE_D[] = {" + ", ".join(f"{x:.2f}" for x in obs_d) + "};",
]
text = "\n".join(lines)

with open("src/storm_data.h", "w") as f:
    f.write(text + "\n")
print(text)