import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import numpy as np
from scipy.fft import fft, fftfreq

# --- Conversion constants ---
MICRONS_PER_PIXEL = 2.083
FRAME_RATE = 226.67  # frames per second
seconds_per_frame = 1 / FRAME_RATE

# --- File selection ---
root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(
    title="Select CSV File",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
)

if not file_path:
    print("No file selected. Exiting.")
    exit()

# --- Load and clean data ---
df = pd.read_csv(file_path, na_values=['None'])
df.columns = df.columns.str.strip()
numeric_cols = ['Centroid_X', 'Centroid_Y', 'Movement (pixels)']
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
df = df.dropna()
df = df.sort_values(by='Frame').reset_index(drop=True)

# --- Convert movement to microns ---
df['Movement (µm)'] = df['Movement (pixels)'] * MICRONS_PER_PIXEL
df['Movement_X (µm)'] = df['Movement_X (dX)'] * MICRONS_PER_PIXEL
df['Movement_Y (µm)'] = df['Movement_Y (dY)'] * MICRONS_PER_PIXEL



# --- Calculate velocity (µm/s) and acceleration (µm/s²) ---
df['Velocity (µm/s)'] = df['Movement (µm)'].diff() / seconds_per_frame
df['Acceleration (µm/s²)'] = df['Velocity (µm/s)'].diff() / seconds_per_frame

# Drop first two rows with NaNs
df = df.dropna().reset_index(drop=True)

# --- Compute average magnitudes ---
avg_speed = df['Velocity (µm/s)'].abs().mean()
avg_accel = df['Acceleration (µm/s²)'].abs().mean()

avg_mx = df['Movement_X (µm)'].abs().mean()
max_mx = df['Movement_X (µm)'].abs().max()

avg_my = df['Movement_Y (µm)'].abs().mean()
max_my = df['Movement_Y (µm)'].abs().max()

avg_m = df['Movement (µm)'].abs().mean()
max_m = df['Movement (µm)'].abs().max()

# --- Calculate displacement vector ---
min_x, min_y = df['Centroid_X'].min() * MICRONS_PER_PIXEL, df['Centroid_Y'].min() * MICRONS_PER_PIXEL
max_x, max_y = df['Centroid_X'].max() * MICRONS_PER_PIXEL, df['Centroid_Y'].max() * MICRONS_PER_PIXEL
disp_vec = (max_x - min_x, max_y - min_y)

# --- Calculate max velocity ---
max_velocity = df['Velocity (µm/s)'].abs().max()

# --- Velocity components for vector field (in microns/frame) ---
vel_x = df['Centroid_X'].diff() * MICRONS_PER_PIXEL
vel_y = df['Centroid_Y'].diff() * MICRONS_PER_PIXEL

# --- Plotting ---
plt.figure(figsize=(20, 12))

# Plot 1: Centroid X and Y (pixels)
plt.subplot(3, 5, 1)
plt.plot(df['Frame'], df['Centroid_X'], label='Centroid X (px)', color='blue')
plt.plot(df['Frame'], df['Centroid_Y'], label='Centroid Y (px)', color='green')
plt.xlabel('Frame')
plt.ylabel('Centroid Position (px)')
plt.title('Centroid X and Y over Frames')
plt.legend()
plt.grid(True)

# Plot 2: Movement X (microns)
plt.subplot(3, 5, 2)
plt.plot(df['Frame'], df['Movement_X (µm)'], color='blue')
plt.axhline(avg_mx, color='gray', linestyle='--', label=f'Avg |X| = {avg_mx:.2f} µm')
plt.axhline(max_mx, color='red', linestyle='--', label=f'Max |X| = {max_mx:.2f} µm')
plt.xlabel('Frame')
plt.ylabel('Movement_X (µm)')
plt.title('X Movement over Frames')
plt.legend()
plt.grid(True)

# Plot 2: Movement Y(microns)
plt.subplot(3, 5, 3)
plt.plot(df['Frame'], df['Movement_Y (µm)'], color='green')
plt.axhline(avg_my, color='gray', linestyle='--', label=f'Avg |Y| = {avg_my:.2f} µm')
plt.axhline(max_my, color='red', linestyle='--', label=f'Max |Y| = {max_my:.2f} µm')
plt.xlabel('Frame')
plt.ylabel('Movement Y (µm)')
plt.title('Y Movement over Frames')
plt.legend()
plt.grid(True)


# Plot 2: Movement (microns)
plt.subplot(3, 5, 4)
plt.plot(df['Frame'], df['Movement (µm)'], color='red')
plt.axhline(avg_m, color='gray', linestyle='--', label=f'Avg = {avg_m:.2f} µm')
plt.axhline(max_m, color='red', linestyle='--', label=f'Max = {max_m:.2f} µm')
plt.xlabel('Frame')
plt.ylabel('Movement (µm)')
plt.title('Movement over Frames')
plt.legend()
plt.grid(True)

# Plot 3: Velocity (µm/s)
plt.subplot(3, 5, 5)
plt.plot(df['Frame'], df['Velocity (µm/s)'], color='orange', label='Velocity')
plt.axhline(avg_speed, color='gray', linestyle='--', label=f'Avg |Speed| = {avg_speed:.2e} µm/s')
plt.axhline(max_velocity, color='red', linestyle='--', label=f'Max Speed = {max_velocity:.2e} µm/s')
plt.xlabel('Frame')
plt.ylabel('Velocity (µm/s)')
plt.title('Velocity over Time')
plt.legend()
plt.grid(True)

# Plot 4: Acceleration (µm/s²)
plt.subplot(3, 5, 6)
plt.plot(df['Frame'], df['Acceleration (µm/s²)'], color='purple', label='Acceleration')
plt.axhline(avg_accel, color='gray', linestyle='--', label=f'Avg |Accel| = {avg_accel:.2e} µm/s²')
plt.xlabel('Frame')
plt.ylabel('Acceleration (µm/s²)')
plt.title('Acceleration over Time')
plt.legend()
plt.grid(True)

# Plot 5: Displacement Vector on Centroid Positions (in microns)
plt.subplot(3, 5, 7)
plt.scatter(df['Centroid_X'] * MICRONS_PER_PIXEL, df['Centroid_Y'] * MICRONS_PER_PIXEL, s=10, alpha=0.5, label='Centroid Positions (µm)')
plt.quiver(
    min_x, min_y,
    disp_vec[0], disp_vec[1],
    angles='xy', scale_units='xy', scale=1,
    color='red', label='Displacement Vector (µm)'
)
plt.xlabel('Centroid X (µm)')
plt.ylabel('Centroid Y (µm)')
plt.title('Displacement Vector on Centroid Positions')
plt.legend()
plt.grid(True)
plt.gca().invert_yaxis()

# Plot 6: Velocity Magnitude Distribution (>30,000 µm/s)
plt.subplot(3, 5, 8)
high_velocities = df['Velocity (µm/s)'].abs()
high_velocities = high_velocities[high_velocities > 30000]
plt.hist(high_velocities, bins=30, color='orange', alpha=0.7)
plt.xlabel('Velocity Magnitude (µm/s)')
plt.ylabel('Frequency')
plt.title('Velocity > 30,000 µm/s')
plt.grid(True)

# Plot 7: Centroid Trajectory Over Time (microns)
plt.subplot(3, 5, 9)
plt.plot(df['Centroid_X'] * MICRONS_PER_PIXEL, df['Centroid_Y'] * MICRONS_PER_PIXEL, marker='o', markersize=3, linestyle='-', color='blue')
plt.xlabel('Centroid X (µm)')
plt.ylabel('Centroid Y (µm)')
plt.title('Centroid Trajectory Over Time')
plt.grid(True)
plt.gca().invert_yaxis()


# Plot 8: Acceleration Magnitude Over Time (µm/s²)
plt.subplot(3, 5, 10)
plt.plot(df['Frame'], df['Acceleration (µm/s²)'].abs(), color='purple')
plt.xlabel('Frame')
plt.ylabel('Acceleration Magnitude (µm/s²)')
plt.title('Acceleration Magnitude Over Time')
plt.grid(True)

# Plot 9: Velocity Vector Field (in microns per frame)
plt.subplot(3, 5, 11)
plt.quiver(df['Centroid_X'][1:] * MICRONS_PER_PIXEL, df['Centroid_Y'][1:] * MICRONS_PER_PIXEL, vel_x[1:], vel_y[1:], angles='xy', scale_units='xy', scale=1, color='green')
plt.xlabel('Centroid X (µm)')
plt.ylabel('Centroid Y (µm)')
plt.title('Velocity Vector Field')
plt.grid(True)
plt.gca().invert_yaxis()

plt.tight_layout()

# Plot 10: Bode plot
# Extract necessary data
frame = df["Frame"].to_numpy()
displacement = df["Movement (pixels)"].to_numpy()
# Assume uniform sampling; estimate time step
dt = (frame[1] - frame[0])  # if ‘frame’ is in time units, otherwise set your dt manually
fs = 1 / dt  # sampling frequency
# FFT of the displacement signal
N = len(displacement)
Y = fft(displacement)
freqs = fftfreq(N, dt)
# Only take the positive half of the frequency spectrum
idx = freqs > 0
freqs = freqs[idx]
Y = Y[idx]
# Calculate magnitude (dB) and phase (degrees)
magnitude = 20 * np.log10(np.abs(Y))
phase = np.angle(Y, deg=True)

"""
# Plot Bode plot
plt.subplot(3, 5, 12)
plt.semilogx(freqs, magnitude)
plt.title("Bode Plot 1:")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude (dB)")
plt.grid(True, which="both")
plt.subplot(3, 5, 13)
plt.semilogx(freqs, phase)
plt.title("Bode Plot 2:")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Phase (degrees)")
plt.grid(True, which="both")
plt.tight_layout()
"""


# ────────────────────────────────────────────────────────────────
#  Bode plots part 2 12 & 13 : centroid_x, centroid_y, displacement
# ────────────────────────────────────────────────────────────────
 
pos_mask     = fftfreq(N, dt) > 0        # keep positive frequencies
# Define the three signals you want to compare -------------------------------
signals = {
    "Centroid X": df['Centroid_X'].to_numpy(),
    "Centroid Y": df['Centroid_Y'].to_numpy(),
    "Displacement": df["Movement (pixels)"].to_numpy()
}
# Allocate storage for results (optional, helps readability) ------------------

pos_mask  = fftfreq(N, dt) > 0
freqs_pos = fftfreq(N, dt)[pos_mask]        # same frequency axis for all

results = {}
for name, vec in signals.items():
    Y2      = fft(vec)[pos_mask]          # FFT of the signal
    freqs2  = fftfreq(N, dt)[pos_mask]    # corresponding positive freqs
    mag    = 20 * np.log10(np.abs(Y))    # magnitude in dB
    phase2  = np.angle(Y2, deg=True)       # phase in degrees
    results[name] = (freqs2, mag, phase2)
# ------------- Plot magnitude overlay  (subplot 12) --------------------------
plt.subplot(3, 5, 12)
for name, (freqs2, mag, _) in results.items():
    plt.semilogx(freqs2, mag, label=name)
plt.title("Bode Plot 1: Magnitude")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude (dB)")
plt.grid(True, which="both", linestyle="--", alpha=0.4)
plt.legend(fontsize="small")
# ------------- Plot phase overlay      (subplot 13) --------------------------
plt.subplot(3, 5, 13)
for name, (freqs2, _, phase2) in results.items():
    plt.semilogx(freqs2, phase2, label=name)
plt.title("Bode Plot 2: Phase")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Phase (°)")
plt.grid(True, which="both", linestyle="--", alpha=0.4)
plt.legend(fontsize="small")
plt.tight_layout()      # keep your existing call here

# ====== NEW :arrow_forward: windowed + phase-unwrapped version ==============================
hann     = np.hanning(N)
Y_win    = fft(displacement * hann)[idx]
mag_win  = 20 * np.log10(np.abs(Y_win))
phase_win= np.unwrap(np.angle(Y_win)) * 180 / np.pi   # unwrap & convert to °
plt.subplot(3, 5, 14)                     # windowed magnitude
plt.semilogx(freqs, mag_win, color="tab:orange")
plt.title("Bode Plot 3: Hann-windowed mag")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude (dB)")
plt.grid(True, which="both")
plt.subplot(3, 5, 15)                     # windowed + unwrapped phase
plt.semilogx(freqs, phase_win, color="tab:orange")
plt.title("Bode Plot 4: Hann-windowed phase (unwrapped)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Phase (°)")
plt.grid(True, which="both")
plt.tight_layout(pad=1.0, w_pad=0.5, h_pad=1.0)
plt.show()