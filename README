# 🛰️ CubeSat 3U Thermal Balance — LEO Orbit Simulation

Streamlit app available online [BY CLICKING HERE](https://cubesat-thermal-vwpo6hrhbzbv3qfzrcvy6r.streamlit.app/)

> **Portfolio project** | Energy Engineering → Space Systems transition  
> Applying industrial thermal-hydraulic modeling methods (EPR2/Edvance) to a CubeSat in LEO.

## What This Demonstrates

| Skill | How it's shown |
|---|---|
| Nodal thermal modeling | 9-node lumped parameter model with full coupling matrix |
| Orbital mechanics | Kepler, eclipse fraction, β-angle, shadow geometry |
| Space thermal environment | Solar flux, albedo, Earth IR, radiative cooling |
| Scientific Python | NumPy, SciPy ODE solver, Plotly, Streamlit |
| Engineering judgment | Sensitivity analysis, thermal margin assessment |
| Industrial workflow | YAML-based config, automated pipeline, reproducible results |

## Physics in 30 Seconds

The CubeSat thermal problem is fundamentally different from building HVAC (my EPR2 background):
**no convection** exists in vacuum. Heat flows only via:
- ☀️ **Absorbed radiation** (Sun + Earth albedo + Earth IR)  
- 🌡️ **Emitted radiation** to deep space (Stefan-Boltzmann)  
- 🔩 **Internal conduction** through structural interfaces

The satellite alternates between eclipse (~36 min) and sunlight (~60 min) every 96-minute orbit,
creating ΔT cycles of 80–110°C on external panels.

## Quick Start

```bash
git clone https://github.com/[username]/cubesat-thermal
cd cubesat-thermal
pip install -r requirements.txt

# Run CLI simulation
python scripts/main_simulation.py

# Or launch interactive dashboard
streamlit run app/app.py