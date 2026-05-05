import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# Load the data
APP_DATA_DIR = "/home/dan/.gemini/antigravity"
CONV_ID = "4a4a6224-4624-401d-b6ed-f3bf06a50bd5"
SCRATCH_DIR = os.path.join(APP_DATA_DIR, "brain", CONV_ID, "scratch")
ARTIFACTS_DIR = os.path.join(APP_DATA_DIR, "brain", CONV_ID, "artifacts")

json_path = os.path.join(SCRATCH_DIR, "xauusd_gamma_4789.json")

with open(json_path, 'r') as f:
    data = json.load(f)

# Extract data
heatmap = data.get('heatmap', [])
regime = data.get('regime', {})
spot = 4789.0 # Use the price provided by the user
db_futures = data.get('underlying_price', 0.0)
flip_raw = regime.get('gamma_flip_level', 0.0)
basis = db_futures - spot
flip_mapped = flip_raw - basis
levels = data.get('levels', [])

df = pd.DataFrame(heatmap)
df = df.sort_values('strike')
df['gex'] = df['call_oi'] - df['put_oi']

# Filter around spot (+/- 300 points)
df_plot = df[(df['mapped_price'] >= spot - 300) & (df['mapped_price'] <= spot + 300)].copy()

# Setup Plot
plt.style.use('dark_background')
fig, ax1 = plt.subplots(figsize=(12, 7))

# Colors
call_color = '#00ff88' 
put_color = '#ff4444'  
gex_color = '#00e5ff'  
spot_color = '#ff1744' # Critical Red for Spot in Neg Gamma
flip_color = '#ff00ff' 

# Bar Plot
ax1.bar(df_plot['mapped_price'], df_plot['call_oi'], width=1.5, alpha=0.3, color=call_color, label='Institutional Call Interest')
ax1.bar(df_plot['mapped_price'], -df_plot['put_oi'], width=1.5, alpha=0.3, color=put_color, label='Institutional Put Interest')

# Net GEX
ax2 = ax1.twinx()
ax2.plot(df_plot['mapped_price'], df_plot['gex'], color=gex_color, linewidth=2.5, label='Net Liquidity Wall (GEX)')
ax2.fill_between(df_plot['mapped_price'], 0, df_plot['gex'], where=(df_plot['gex'] >= 0), color=gex_color, alpha=0.15)
ax2.fill_between(df_plot['mapped_price'], 0, df_plot['gex'], where=(df_plot['gex'] < 0), color='#ff9100', alpha=0.15)

# Mark Levels
ax1.axvline(x=spot, color=spot_color, linestyle='--', linewidth=3, label=f'Current Spot: ${spot:,.2f}')
ax1.axvline(x=flip_mapped, color=flip_color, linestyle=':', linewidth=2, label=f'Mapped Flip: ${flip_mapped:,.2f}')

# Mark Major Walls
for level in levels:
    if level['type'] in ['CALL_WALL', 'PUT_WALL'] and level['zone_type'] == 'MAJOR':
        if spot - 300 <= level['price'] <= spot + 300:
            ax1.axvline(x=level['price'], color='white', alpha=0.4, linestyle='-')
            ax1.text(level['price'], ax1.get_ylim()[1]*0.8, f"{level['type']}\n${level['price']:.0f}", 
                     color='white', horizontalalignment='center', fontweight='bold', fontsize=8)

# Formatting
ax1.set_xlabel('Mapped Gold Price (USD)', fontsize=12, fontweight='bold')
ax1.set_ylabel('OI Strength (Contracts)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Net Liquidity Density', fontsize=12, fontweight='bold')
plt.title(f'REGIME SHIFT ALERT: XAU/USD @ 4789\nRegime: {regime.get("regime", "UNKNOWN")} (VOLATILITY EXPANSION)', fontsize=16, pad=20, fontweight='bold', color='#ff1744')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, framealpha=0.6)

plt.grid(alpha=0.05)
plt.tight_layout()

# Save image
output_path = os.path.join(ARTIFACTS_DIR, "xau_regime_shift_4789.png")
plt.savefig(output_path, dpi=200)
print(f"Chart saved to: {output_path}")
