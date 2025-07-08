import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time
import csv

# ==== CONFIGURATION ====
V_START = 0.5        # Start voltage (V)
V_STOP = 22.0        # Stop voltage (adjust based on your solar panel Voc)
V_STEP = 0.5         # Step size (V)
DWELL_TIME = 0.3     # Wait time after setting load before measuring
ESTIMATED_CURRENT = 5  # Max expected current in Amps (used for resistance calc)
CSV_FILENAME = "iv_pv_data.csv"

# ==== VISA SETUP ====
rm = pyvisa.ResourceManager()
usb_instruments = [r for r in rm.list_resources() if 'USB' in r]

if not usb_instruments:
    raise RuntimeError("No USB instruments found. Check connections and drivers.")

resource = usb_instruments[0]
print(f"Connecting to: {resource}")
inst = rm.open_resource(resource)

# Optional: tune VISA comms
inst.timeout = 5000  # milliseconds
inst.write_termination = '\n'
inst.read_termination = '\n'

# ==== VERIFY COMMUNICATION ====
print("Instrument ID:", inst.query("*IDN?"))

# ==== LOAD SETUP ====
inst.write(":FUNC RES")     # Set to Constant Resistance mode
inst.write(":INPUT ON")     # Turn on the electronic load

voltages = []
currents = []
powers = []

# ==== SWEEP LOOP ====
print("\nStarting sweep...\n")
for v_target in np.arange(V_START, V_STOP + V_STEP, V_STEP):
    if v_target == 0:
        resistance = 0.01  # prevent division by zero
    else:
        resistance = v_target / ESTIMATED_CURRENT

    inst.write(f":RES {resistance:.3f}")
    time.sleep(DWELL_TIME)

    # Measure
    voltage = float(inst.query(":MEAS:VOLT?"))
    current = float(inst.query(":MEAS:CURR?"))
    power = voltage * current

    voltages.append(voltage)
    currents.append(current)
    powers.append(power)

    print(f"V={voltage:.2f} V | I={current:.2f} A | P={power:.2f} W")

inst.write(":INPUT OFF")  # Turn off load

# ==== MPP DETECTION ====
voltages = np.array(voltages)
currents = np.array(currents)
powers = np.array(powers)

max_idx = np.argmax(powers)
v_mpp = voltages[max_idx]
i_mpp = currents[max_idx]
p_mpp = powers[max_idx]

print(f"\n==> Maximum Power Point (MPP): {p_mpp:.2f} W at {v_mpp:.2f} V, {i_mpp:.2f} A")

# ==== PROMPT TO SAVE CSV ====
save_input = input("\nWould you like to save the I-V/P-V data to CSV? (y/n): ").strip().lower()

if save_input == 'y':
    with open(CSV_FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Voltage (V)", "Current (A)", "Power (W)"])
        writer.writerows(zip(voltages, currents, powers))
    print(f"✅ Data saved to {CSV_FILENAME}")
else:
    print("❌ CSV not saved.")

# ==== PLOTTING ====
plt.figure(figsize=(12, 6))

# I-V curve
plt.subplot(1, 2, 1)
plt.plot(voltages, currents, 'b.-')
plt.title('I-V Curve')
plt.xlabel('Voltage (V)')
plt.ylabel('Current (A)')
plt.grid(True)

# P-V curve
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
