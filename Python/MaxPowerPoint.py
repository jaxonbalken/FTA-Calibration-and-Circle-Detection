import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time
import csv
from datetime import datetime

# ==== CONFIGURATION ====
I_START = 0.0         # Start current (A)
I_STOP = 5.0          # Max current (A) - adjust based on panel rating
I_STEP = 0.1          # Step size (A)
DWELL_TIME = 0.3      # Wait time between current steps (seconds)
V_MIN_CUTOFF = 1.0    # Minimum voltage to continue sweep (safety cutoff)
CSV_BASE_FILENAME = "solar_iv_pv_data"
MAX_RETRIES = 3       # How many times to retry if conditions are unstable

# ==== CONNECT TO INSTRUMENT ====
rm = pyvisa.ResourceManager()
usb_instruments = [r for r in rm.list_resources() if 'USB' in r]

if not usb_instruments:
    raise RuntimeError("No USB instruments found. Check connections and drivers.")

resource = usb_instruments[0]
print(f"Connecting to: {resource}")
inst = rm.open_resource(resource)
inst.timeout = 5000
inst.write_termination = '\n'
inst.read_termination = '\n'

# ==== IDENTIFY DEVICE ====
print("Instrument ID:", inst.query("*IDN?"))

# ==== MEASURE OPEN-CIRCUIT VOLTAGE (Voc) ====
def measure_voc():
    inst.write(":INPUT OFF")      # Ensure no load is applied
    time.sleep(1)
    voc = float(inst.query(":MEAS:VOLT?"))
    print(f"🌤️  Measured Voc (open-circuit voltage): {voc:.2f} V")
    return voc

# ==== PERFORM DYNAMIC CURRENT SWEEP ====
def run_iv_sweep(voc_estimate):
    current_steps = np.arange(I_START, I_STOP + I_STEP, I_STEP)
    voltages = []
    currents = []
    powers = []

    inst.write(":FUNC CURR")       # Set to Constant Current mode
    inst.write(":INPUT ON")        # Turn on electronic load

    for i in current_steps:
        inst.write(f":CURR {i:.3f}")   # Set current
        time.sleep(DWELL_TIME)

        voltage = float(inst.query(":MEAS:VOLT?"))  # Measure voltage
        current = i
        power = voltage * current

        # Abort if panel voltage collapses (e.g., from shading)
        if voltage < V_MIN_CUTOFF:
            print(f"⚠️  Voltage dropped below {V_MIN_CUTOFF}V. Aborting sweep.")
            break

        voltages.append(voltage)
        currents.append(current)
        powers.append(power)

        print(f"I={current:.2f} A | V={voltage:.2f} V | P={power:.2f} W")

    inst.write(":INPUT OFF")   # Turn off electronic load
    return np.array(currents), np.array(voltages), np.array(powers)

# ==== MAIN TEST LOOP WITH RETRIES IF CONDITIONS CHANGE ====
for attempt in range(1, MAX_RETRIES + 1):
    print(f"\n===== SWEEP ATTEMPT {attempt} =====\n")
    
    voc = measure_voc()
    if voc < V_MIN_CUTOFF + 2:
        print("⚠️  Voc too low. Waiting for better sunlight...")
        time.sleep(10)
        continue  # Retry

    currents, voltages, powers = run_iv_sweep(voc)
    if len(voltages) < 5:
        print("⚠️  Not enough valid points. Retrying...")
        time.sleep(10)
        continue  # Retry

    break  # Success

else:
    print("❌ Could not complete a valid sweep. Check panel or light conditions.")
    exit()

# ==== FIND MAXIMUM POWER POINT (MPP) ====
max_idx = np.argmax(powers)
v_mpp = voltages[max_idx]
i_mpp = currents[max_idx]
p_mpp = powers[max_idx]

print(f"\n✅ Maximum Power Point (MPP): {p_mpp:.2f} W at {v_mpp:.2f} V, {i_mpp:.2f} A")

# ==== PROMPT TO SAVE DATA TO CSV ====
save_input = input("\n💾 Save data to CSV? (y/n): ").strip().lower()
if save_input == 'y':
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CSV_BASE_FILENAME}_{timestamp}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Current (A)", "Voltage (V)", "Power (W)", "Voc (V)", "Timestamp"])
        for i, v, p in zip(currents, voltages, powers):
            writer.writerow([i, v, p, voc, timestamp])
    print(f"✅ Data saved to {filename}")
else:
    print("❌ Data not saved.")

# ==== PLOT I-V AND P-V CURVES ====
plt.figure(figsize=(12, 6))

# I-V Curve
plt.subplot(1, 2, 1)
plt.plot(voltages, currents, 'b.-')
plt.title('I-V Curve')
plt.xlabel('Voltage (V)')
plt.ylabel('Current (A)')
plt.grid(True)

# P-V Curve
plt.subplot(1, 2, 2)
plt.plot(voltages, powers, 'r.-')
plt.plot(v_mpp, p_mpp, 'ko', label=f'MPP: {p_mpp:.2f}W at {v_mpp:.2f}V')
plt.title('P-V Curve')
plt.xlabel('Voltage (V)')
plt.ylabel('Power (W)')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

# ------------------------------------------------------------------------------
# Solar Panel IV/PV Characterization Script (Rigol DL3031 - Dynamic Current Mode)
#
# ✅ Performs a safe dynamic current sweep using CC mode (0 A to max A)
# ✅ Automatically logs Voc (open-circuit voltage) as a proxy for sunlight intensity
# ✅ Aborts sweep if voltage collapses (e.g., due to shading or cloud cover)
# ✅ Retries sweep up to 3 times if conditions are unstable
# ✅ Identifies Maximum Power Point (MPP) and displays it
# ✅ Prompts to save data (timestamped CSV with Voc and time)
# ✅ Plots I-V and P-V curves with MPP highlighted
# ✅ Designed for real-time field testing under changing sunlight
# ------------------------------------------------------------------------------
