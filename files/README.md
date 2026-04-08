# GB Grid Monitor

A Python tool and live web dashboard that pulls real-time electricity generation and carbon intensity data from the National Energy System Operator (NESO) public API, visualising the current UK generation mix, carbon intensity rating, and today's half-hourly trend.

Built as part of a portfolio ahead of a Junior Power Systems Engineer placement at National Grid.

---

## What it does

- Fetches live data from `api.carbonintensity.org.uk` (public API, no authentication required)
- Displays the current generation mix across nine fuel types: wind, solar, nuclear, gas, coal, hydro, biomass, imports, and other
- Shows the current carbon intensity in gCO₂eq/kWh alongside its qualitative index (very low → very high)
- Plots today's half-hourly intensity trend with min/max/average annotations
- Computes the renewable, low-carbon, and fossil fuel split for the current half-hour

---

## Why this matters for power systems

The UK electricity grid is undergoing a fundamental transition. As coal exits the generation mix and wind/solar capacity grows, the system operator faces new challenges in balancing supply and demand in real time. Carbon intensity — the grams of CO₂ equivalent emitted per kilowatt-hour of electricity generated — provides a direct measure of how clean the grid is at any given moment.

This tool makes several key relationships visible:

**Intermittency and the residual load.** When wind and solar output is high, carbon intensity drops and gas generation is displaced. When renewable output falls (low wind overnight, no solar), gas turbines ramp up to meet demand, pushing intensity higher. This pattern is visible in the daily trend chart.

**The role of nuclear and imports.** Nuclear provides constant low-carbon baseload, smoothing out the intensity curve regardless of renewable conditions. Interconnector imports (from France, Belgium, Norway, and the Netherlands) can be either low- or high-carbon depending on the source country's generation mix at that moment — which is why imports appear as a separate category rather than being folded into renewables.

**Implications for grid balancing.** National Grid ESO (now NESO) must ensure supply matches demand at all times, maintaining grid frequency at 50 Hz ± 0.2 Hz. As variable renewables displace dispatchable generation, maintaining system inertia and procuring frequency response services becomes more complex. The generation mix visible here is the direct output of that balancing process.

---

## Technical overview

| Component | Detail |
|---|---|
| Data source | Carbon Intensity API (carbonintensity.org.uk) — a joint project by National Grid ESO, Environmental Defence Fund Europe, Oxford University, and WWF |
| API style | RESTful JSON, no authentication, 30-minute resolution |
| Key endpoints | `/intensity` · `/generation` · `/intensity/date` |
| Python dependencies | `requests`, `matplotlib` |
| Web dashboard | Single-file HTML/CSS/JS, no build step, no dependencies |

### Endpoints used

```
GET https://api.carbonintensity.org.uk/intensity
    → Current half-hour carbon intensity (forecast, actual, index)

GET https://api.carbonintensity.org.uk/generation
    → Current generation mix by fuel type (% share)

GET https://api.carbonintensity.org.uk/intensity/date
    → Today's half-hourly intensity data (48 data points)
```

---

## Installation and usage

```bash
# Clone the repository
git clone https://github.com/your-username/gb-grid-monitor.git
cd gb-grid-monitor

# Install dependencies
pip install requests matplotlib

# Print a live summary to terminal
python grid_monitor.py

# Save a plot to grid_monitor.png
python grid_monitor.py --plot

# Save and open the plot interactively
python grid_monitor.py --plot --show

# Specify a custom output path
python grid_monitor.py --plot --output ~/Desktop/grid_snapshot.png
```

### Example terminal output

```
========================================================
  GB Grid Monitor  —  National Energy System Operator
========================================================
  Timestamp : 2026-04-08T14:00Z  (UTC)

  CARBON INTENSITY
    Current  : 142 gCO₂eq/kWh  [LOW]
    Forecast : 145 gCO₂eq/kWh

  GENERATION MIX
    wind      ##############################   32.1%
    gas       #####################            22.3%
    nuclear   ##################               18.4%
    imports   ########                          8.7%
    solar     ######                            6.2%
    other     #####                             5.3%
    biomass   #####                             5.1%
    hydro     ##                                1.9%
    coal                                        0.0%

  MIX SUMMARY
    Renewables  : 45.3%
    Fossil      : 22.3%
    Low-carbon  : 63.7%

  TODAY'S TREND
    Min : 130 gCO₂eq/kWh
    Max : 215 gCO₂eq/kWh
    Avg : 168 gCO₂eq/kWh
========================================================
```

---

## Project structure

```
gb-grid-monitor/
├── grid_monitor.py       # Python CLI script
├── index.html            # Live web dashboard (single file)
├── README.md             # This file
└── grid_monitor.png      # Example output (generated by --plot)
```

---

## Carbon intensity index thresholds

| Index | Range (gCO₂eq/kWh) |
|---|---|
| Very low | 0 – 50 |
| Low | 50 – 100 |
| Moderate | 100 – 200 |
| High | 200 – 300 |
| Very high | > 300 |

These thresholds are defined by the Carbon Intensity API project and align with the UK's grid decarbonisation trajectory under the Sixth Carbon Budget.

---

## Possible extensions

- Regional breakdown — the API provides intensity data per DNO region (14 zones across GB)
- Demand overlay — combine with the NESO Data Portal to show demand vs generation
- Frequency data — pull system frequency from the NESO Data Portal to visualise inertia events
- Price signal — overlay day-ahead wholesale prices to correlate intensity with market conditions
- Alerts — trigger a notification when intensity drops below a threshold (good time to run high-consumption appliances or charge EVs)

---

## Data attribution

Carbon intensity data provided by the [Carbon Intensity API](https://carbonintensity.org.uk), a project by National Grid ESO, Environmental Defence Fund Europe, University of Oxford, and WWF-UK. Generation mix data sourced from the same API. All data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
