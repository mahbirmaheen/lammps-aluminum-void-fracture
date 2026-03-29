import pandas as pd

input_file = "flow_stress_vs_strain.txt"

data = []
with open(input_file, "r") as f:
    for line in f:
        if line.startswith("#") or line.strip() == "":
            continue
        
        parts = line.split()
        
        step = int(parts[0])
        strain = float(parts[1])
        
        #Convert stress to positive here
        stress = abs(float(parts[2]))
        # OR: stress = -float(parts[2])

        data.append([step, strain, stress])

# Create DataFrame
df = pd.DataFrame(data, columns=["Step", "Strain(%)", "Flow Stress(GPa)"])

# Save CSV
df.to_csv("stress_strain_positive.csv", index=False)

print("CSV with positive stress created!")