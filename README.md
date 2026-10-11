# Lightning Warning Box

A low-cost lightning warning device for outdoor workers such as farmers. It answers two questions from nothing but lightning-strike reports (time and estimated distance):

1. **How long until the storm reaches me?** (shelter countdown)
2. **When is it safe to go back out?** (adaptive all-clear, instead of the fixed 30-minute rule)

It shows one of three states: **GREEN** (no danger), **YELLOW** (storm nearby, or still inside the all-clear wait) and **RED** (take shelter now, with a buzzer).

Submitted to the FOSSEE Make-A-Thon 2026 (theme: open-source hardware for natural-disaster detection and early warning).

> **Please read first: what this project is and is not.**
> There is no physical hardware and no real storm data. The device is a circuit design plus firmware, run in an online simulator, and all statistical results come from *simulated* storms. Results therefore reflect my modelling assumptions (listed under [Limitations](#limitations)) and have not been validated on real lightning data.

## Contents

- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Results](#results)
- [Hardware design](#hardware-design)
- [Limitations](#limitations)
- [Prior work](#prior-work)
- [How to reproduce](#how-to-reproduce)
- [Licence](#licence)

## How it works

**Simulated storms** (`src/simulator.py`). A storm cell moves in a straight line past the device. Strikes arrive as a Poisson process whose rate rises and falls like a bell curve. The sensor model adds three imperfections: 20% of strikes are missed, distance error grows with distance (about 10%), and false triggers occur at random (about 0.05 per minute, at random distances up to 40 km).

**Bursty storms** (`src/bursty.py`). A harder test set where each storm alternates between active spells (mean 6 min) and quiet spells (mean 8 min, 5% of the normal rate), keeping the long-run average rate the same.

**Shelter countdown** (`src/countdown.py`). Fits a line through the last 20 minutes of strike distances, drops outliers (false triggers), and extrapolates to a 10 km threat distance.

**All-clear rules** (`src/allclear.py`, `src/tradeoff_v2.py`, `src/tradeoff_v3.py`). Three families were compared against the fixed 30-minute rule, all based on strikes within 16 km:

- *Mean-gap rule:* wait = k x the mean gap between recent close strikes (clipped to 5-30 min).
- *Max-gap rule:* wait = m x the longest gap seen so far in the storm (clipped to 5-30 min).
- *Path rule:* fit the storm's distance trend and wait until the projected distance passes a margin (22 or 26 km). If the storm is not clearly moving away, wait the full 30 minutes.

**Alert logic** (`src/alert.py`).

- RED: two strikes within 10 km in the last 5 minutes, or a countdown of 10 minutes or less (ignored if strikes are clearly receding). RED is held for at least 10 minutes to stop flicker.
- YELLOW: strikes within 30 km before the storm gets close, or still inside the adaptive all-clear wait afterwards.
- GREEN: otherwise.

The device and the Python reference implementation use the **mean-gap rule with k = 12**. See [Limitations](#limitations) for why this matters.

## Repository layout

src/
  simulator.py            smooth storm + noisy sensor model
  bursty.py               bursty storm model
  countdown.py            shelter countdown
  evaluate_countdown.py   countdown accuracy over 100 storms
  allclear.py             fixed and mean-gap all-clear rules
  tradeoff.py             safety vs time-saved, smooth storms
  tradeoff_bursty.py      same, smooth vs bursty
  tradeoff_v2.py          adds the max-gap rule
  tradeoff_v3.py          adds the path rule
  holdout.py              final comparison on 500 + 500 fresh storms
  alert.py                GREEN / YELLOW / RED logic
  evaluate_alert.py       full alert system vs the fixed rule
  diagnose*.py            diagnostics used while debugging (see notes below)
  export_storm.py         writes a storm as a C header for the firmware
hardware/
  lightning-box.*         KiCad project (schematic)
  lightning-box.pdf           exported schematic
wokwi/
  sketch.ino, diagram.json, storm_data.h    ESP32 firmware and circuit
                          (export_storm.py writes storm_data.h into src/; copy it here)
tradeoff.png, tradeoff_bursty.png, tradeoff_v2.png    result plots (repository root)

## Results

All numbers come from the simulation. "Unsafe" means a real strike within 16 km happened *after* the device declared all-clear. "Saved" is the average number of minutes earlier than the fixed 30-minute rule.

### Shelter countdown (100 smooth storms)

| Minutes before arrival | Storms | No estimate | Median error | Median absolute error |
|---|---|---|---|---|
| 30 | 53 | 41 | +1.8 min | 15.0 min |
| 20 | 58 | 20 | -4.5 min | 8.6 min |
| 10 | 59 | 6 | -2.1 min | 3.6 min |
| 5 | 59 | 4 | -1.7 min | 3.0 min |

The countdown is useful within about 10 minutes of arrival (median error around 3 minutes, slightly on the early, safe side). Far out it mostly gives no estimate because too few strikes have arrived. A small number of estimates are dangerously wrong, saying there is plenty of time when the storm is nearly overhead.

### All-clear rules on fresh storms

Rules were tuned on 200 storms and then tested on 500 fresh smooth and 499 fresh bursty storms never used during tuning (`src/holdout.py`).

| Rule | Smooth: unsafe / saved | Bursty: unsafe / saved |
|---|---|---|
| Fixed 30-minute rule | 7.4% / 0 | 8.8% / 0 |
| Mean-gap, k = 12 (**used in the firmware**) | 10.8% / 14.5 min | **64.9%** / 45.0 min |
| Max-gap, m = 3 | 8.8% / 10.0 min | 29.9% / 18.4 min |
| Path rule, margin 22 km | 9.6% / 17.5 min | 11.0% / 15.3 min |
| Path rule, margin 26 km | 8.6% / 11.4 min | 10.2% / 10.2 min |

Key findings:

- On smooth storms, the mean-gap rule saves roughly 15 minutes at a safety level close to the fixed rule.
- **On bursty storms, the mean-gap rule fails badly.** It mistakes a lull for the end of the storm and clears during the storm in over half of cases. Its large time saving there is not real.
- The path rule held up on bursty storms (11.0% unsafe, 15.3 minutes saved) because it tracks where the storm is going, not only how often it strikes. It is still slightly less safe than the fixed rule, so the honest claim is "close to the fixed rule's safety with 10-17 minutes saved", not "as safe".
- The earlier tuning-set result for the mean-gap rule (8.5% unsafe) was optimistic. On fresh storms it was 10.8%.

### Full alert system (mean-gap rule, 200 smooth storms)

| | Unsafe | Saved vs fixed rule |
|---|---|---|
| Fixed 30-minute rule | 8.0% | 0 |
| Full alert system | 7.5% | 13.7 min (median 12.1) |

The 0.5-point difference is one storm in 200 and should not be read as a safety improvement.

### Where the "unsafe" storms come from (200 smooth storms)

| | Safe | Cleared before the real storm | Cleared mid-storm |
|---|---|---|---|
| Fixed 30-minute rule | 92.0% | 7.0% | 1.0% |
| Mean-gap, k = 12 | 91.5% | 7.0% | 1.5% |

Most unsafe cases are the device clearing *before* the real storm arrives. I did not trace each one, but my best explanation is a false trigger within 16 km starting the all-clear clock while the real storm is still far away (in 82 of 200 storms the first close strike the sensor reported was a false one). Clearing during the storm is rare on smooth storms.

### Plots

- `tradeoff.png`: safety vs time saved for the mean-gap rule (smooth storms)
- `tradeoff_bursty.png`: smooth vs bursty
- `tradeoff_v2.png`: mean-gap vs max-gap rules

## Hardware design

- **Microcontroller:** ESP32 (WROOM-32 module)
- **Indicators:** green, yellow and red LEDs on IO25, IO26, IO27, each through a 220 ohm resistor to ground; buzzer on IO14 (sounds during RED)
- **Lightning sensor:** AS3935 on SPI: SCK to IO18, MISO to IO19, MOSI to IO23, CS to IO5, IRQ to IO4. SI is tied to ground to select SPI mode, EN to 3.3 V.

The schematic is in `hardware/` (KiCad). The firmware and circuit run in the Wokwi simulator.

**Simulation notes:**

- I did not use an AS3935 part in Wokwi (a web search turned up none, but I did not check Wokwi's parts list exhaustively), so the firmware does not read a sensor. It **replays a stored strike list** (`storm_data.h`, exported from the Python simulator, storm seed 1) through the same alert logic, with 1 simulated minute = 0.5 s.
- Python produces state changes at minutes 0 (GREEN), 14 (YELLOW), 24 (RED), 61 (YELLOW) and 74 (GREEN) for this storm. **Partial check only:** in the simulator I saw the green LED lit near the end of a fast replay (Python predicts GREEN from minute 74 on) and the red LED lit about 18 s into a replay at 0.5 s per minute (Python predicts RED from about 12 s to 30 s). I did not time every transition, and I could not get the Serial Monitor output to display, so the firmware has not been confirmed to reproduce the full Python sequence.
- Wokwi is free but **not open source**. The code, schematic and circuit description are open, but anyone reproducing the simulation needs a Wokwi account.

**Not yet verified against datasheets:** the AS3935 pin functions used here (SI to ground for SPI, EN to Vdd, grounding the exposed pad) were set from memory, and I could not confirm them from the datasheet. The symbol is the bare chip, so the antenna and regulator pins (ACG, IN-, IN+, VReg, AD0, AD1) are left open. A real build would use a breakout module that already provides them, and its pin order and wiring should be checked first. KiCad's electrical rules check also reports the unused ESP32 pins and these open sensor pins, which are intentional.

## Limitations

- **Everything is simulated.** Storm path, strike process, burst timing and the false-trigger rate are my assumptions, not measured. The burst parameters in particular were chosen to be hard, and results could change a lot with different values.
- **Straight-line storm motion.** The simulator moves storms at constant speed in a straight line, which flatters the path rule. Real storms change speed and direction.
- **The firmware uses the weaker rule.** The mean-gap rule (k = 12) runs on the device and in `alert.py` because it was built first. The path rule performs better on bursty storms but is **not ported to the firmware**.
- **Re-alerting.** In 70 of 200 smooth storms the device returned to YELLOW or RED after its first GREEN, mostly because of a single false trigger. A confirmation filter reduced this only slightly (to 56) while raising unsafe cases to 13.5%, so I reverted it.
- **Countdown tail risk.** A few countdown estimates were off by an hour or more in the unsafe direction.
- **Tuning and test data.** Settings (k = 12, margins 22 and 26 km) were chosen by looking at results on the tuning storms. Only the final comparison used fresh storms.
- **Safety.** This is a student project and must not be used as a real safety device.

## Prior work

This project does not claim to invent lightning detection. Existing work includes IITM Pune's Damini lightning-alert app (built on a national lightning-location sensor network, it sends GPS-based alerts when lightning occurs within 20 km and 40 km of the user), the volunteer Blitzortung.org network (community-run VLF receivers whose strikes are located from time of arrival), and projects built around the AS3935 lightning-sensor chip. Commercial lightning detectors also exist; I have not surveyed them. I have not done a literature search on adaptive all-clear rules, so I make no novelty claim for them. What this repository adds is an open, reproducible evaluation of all-clear rules against the fixed 30-minute rule, including the failure on bursty storms.

## How to reproduce

Requires Python 3 with `numpy` and `matplotlib`.

pip install numpy matplotlib
python src/evaluate_countdown.py
python src/tradeoff.py
python src/tradeoff_bursty.py
python src/tradeoff_v2.py
python src/tradeoff_v3.py
python src/holdout.py
python src/evaluate_alert.py

Run scripts from the repository root. Each script is seeded, so the printed numbers should match the tables above. The `diagnose*.py` scripts are the debugging tools I used to find an evaluation mistake early on (measuring the last GREEN instead of the first GREEN gave a false 0% unsafe result).

## Licence

MIT (add a `LICENSE` file to the repository root).

## Author

Ananya Makkar
