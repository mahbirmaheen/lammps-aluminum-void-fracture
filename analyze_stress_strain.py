import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.optimize import curve_fit

# LOAD DATA

input_file = "flow_stress_vs_strain.txt"

steps, strains, stresses_raw = [], [], []

with open(input_file, "r") as f:
    for line in f:
        if line.startswith("#") or line.strip() == "":
            continue
        parts = line.split()
        steps.append(int(parts[0]))
        strains.append(float(parts[1]))
        stresses_raw.append(float(parts[2]))   # these are NEGATIVE in tension

# Convert to numpy arrays
steps    = np.array(steps)
strains  = np.array(strains)    # in %
stresses = np.abs(stresses_raw) # take absolute value → positive flow stress

# 2. FIND PEAK FLOW STRESS AND STRAIN AT PEAK
# np.argmax returns the index of the largest value in the array.
# Since stresses is now positive (abs), the max IS the peak flow stress.

peak_idx          = np.argmax(stresses)
peak_flow_stress  = stresses[peak_idx]   # GPa
strain_at_peak    = strains[peak_idx]    # %
step_at_peak      = steps[peak_idx]

print("=" * 50)
print("  KEY MECHANICAL PROPERTIES")
print("=" * 50)
print(f"  Peak flow stress  : {peak_flow_stress:.4f} GPa")
print(f"  Strain at peak    : {strain_at_peak:.2f} %")
print(f"  LAMMPS step       : {step_at_peak}")
print(f"  Total data points : {len(stresses)}")
print()

# 3. ADDITIONAL PROPERTIES

# Initial flow stress (first non-zero point after relaxation)
initial_stress = stresses[1]   # step 100 (first loading step)

# Final flow stress at 10% strain
final_stress   = stresses[-1]

# Stress drop from peak to final (softening magnitude)
stress_drop    = peak_flow_stress - final_stress
stress_drop_pct = (stress_drop / peak_flow_stress) * 100

# Approximate elastic modulus from the initial linear region (steps 0→peak)
# Using linear fit on the first ~10 data points
linear_region_idx = 10   # adjust based on your data
m, c = np.polyfit(strains[1:linear_region_idx],
                  stresses[1:linear_region_idx], 1)
approx_modulus = m   # GPa/% → multiply by 100 to get GPa (true strain units)

print(f"  Initial stress (ε=0.1%) : {initial_stress:.4f} GPa")
print(f"  Final stress  (ε=10%)   : {final_stress:.4f} GPa")
print(f"  Stress drop from peak   : {stress_drop:.4f} GPa ({stress_drop_pct:.1f}%)")
print(f"  Approx. elastic slope   : {m:.4f} GPa/%")
print()

# FIT A SMOOTH CURVE (Johnson-Cook inspired — polynomial fit)

def model_stress(eps, A, B, n, C, m_exp):
    """
    Custom phenomenological fit: σ = A * eps^n * exp(-B * eps^m)
    Captures rise → peak → softening shape of void-driven fracture curves.
    """
    eps = np.where(eps <= 0, 1e-9, eps)
    return A * (eps ** n) * np.exp(-B * (eps ** m_exp)) + C

# Fit to data excluding the initial zero point
try:
    popt, _ = curve_fit(
        model_stress,
        strains[1:],
        stresses[1:],
        p0=[20, 0.3, 0.5, 0.1, 1.0],
        maxfev=10000
    )
    eps_fit   = np.linspace(0.01, 10, 500)
    sigma_fit = model_stress(eps_fit, *popt)
    fit_available = True
    print(f"  Curve fit converged. Parameters: {np.round(popt, 4)}")
except Exception as e:
    fit_available = False
    print(f"  Curve fit did not converge: {e}. Plotting data only.")

print()

#PLOT

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor("#1a1a2e")
ax.set_facecolor("#16213e")

# Data scatter
ax.scatter(strains, stresses, color="#e94560", s=18, zorder=5,
           label="Flow Stress (GPa) — MD data", alpha=0.85)

# Fitted curve
if fit_available:
    ax.plot(eps_fit, sigma_fit, color="#e94560", linewidth=2.0,
            label="Phenomenological fit", alpha=0.9)

#Peak annotation
ax.annotate(
    f"Peak: {peak_flow_stress:.3f} GPa\nat ε = {strain_at_peak:.1f}%",
    xy=(strain_at_peak, peak_flow_stress),
    xytext=(strain_at_peak + 1.5, peak_flow_stress - 1.0),
    fontsize=10,
    color="white",
    arrowprops=dict(arrowstyle="->", color="#f5a623", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#f5a623",
              edgecolor="none", alpha=0.85),
)
ax.axvline(x=strain_at_peak, color="#f5a623", linewidth=0.8,
           linestyle="--", alpha=0.5)
ax.axhline(y=peak_flow_stress, color="#f5a623", linewidth=0.8,
           linestyle="--", alpha=0.5)

# Region shading 
ax.axvspan(0, strain_at_peak, alpha=0.07, color="#00b4d8",
           label=f"Elastic/hardening (0 – {strain_at_peak:.1f}%)")
ax.axvspan(strain_at_peak, 10, alpha=0.07, color="#e94560",
           label="Void growth & softening")

#Labels, grid, legend
ax.set_xlabel("Strain (%)", fontsize=13, color="white")
ax.set_ylabel("Flow Stress (GPa)", fontsize=13, color="white")
ax.set_title("Flow Stress vs. Strain — FCC Aluminum with Central Void\n"
             "LAMMPS · EAM/Alloy · 300 K · 10 ps",
             fontsize=13, color="white", pad=14)

ax.tick_params(colors="white", labelsize=10)
for spine in ax.spines.values():
    spine.set_edgecolor("#444")

ax.grid(True, color="#2a2a4a", linewidth=0.6, linestyle="--", alpha=0.8)
ax.set_xlim(-0.2, 10.5)
ax.set_ylim(-0.3, peak_flow_stress * 1.12)

legend = ax.legend(fontsize=9, framealpha=0.3,
                   facecolor="#1a1a2e", edgecolor="#444",
                   labelcolor="white", loc="upper right")

plt.tight_layout()
plt.savefig("stress_strain_analysis.png", dpi=150,
            bbox_inches="tight", facecolor=fig.get_facecolor())
plt.show()
print("Plot saved as stress_strain_analysis.png")

# 
#SAVE CLEAN CSV WITH ALL PROPERTIES
# 

df = pd.DataFrame({
    "Step":               steps,
    "Strain (%)":         strains,
    "Flow Stress (GPa)":  stresses,
    "Raw Stress (GPa)":   stresses_raw
})

df.to_csv("stress_strain_positive.csv", index=False)
print("CSV saved as stress_strain_positive.csv")

# Save a summary file
summary = {
    "Property":        ["Peak flow stress (GPa)",
                        "Strain at peak (%)",
                        "LAMMPS step at peak",
                        "Initial stress at ε=0.1% (GPa)",
                        "Final stress at ε=10% (GPa)",
                        "Stress drop from peak (GPa)",
                        "Stress drop from peak (%)"],
    "Value":           [f"{peak_flow_stress:.4f}",
                        f"{strain_at_peak:.2f}",
                        f"{step_at_peak}",
                        f"{initial_stress:.4f}",
                        f"{final_stress:.4f}",
                        f"{stress_drop:.4f}",
                        f"{stress_drop_pct:.1f}"]
}

df_summary = pd.DataFrame(summary)
df_summary.to_csv("mechanical_properties_summary.csv", index=False)
print("Summary saved as mechanical_properties_summary.csv")
print()
print("Done.")
