import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from pathlib import Path
from tkinter import Tk, filedialog

# ─────── File Picker ───────
def select_csv_file():
    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="Select Combined CSV", filetypes=[("CSV files", "*.csv")])
    root.destroy()
    if not path:
        raise FileNotFoundError("File selection cancelled.")
    return Path(path)

# ─────── XY Displacement (Microns) ───────
def plot_xy_displacement(df, frame_col):
    fig, axs = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.suptitle("X and Y Displacement in Microns", fontsize=14)

    for i, axis in enumerate(["dX (Microns)", "dY (Microns)"]):
        if axis not in df.columns:
            print(f"Missing column: {axis}")
            continue

        x = df[frame_col]
        y = df[axis]

        # Ignore abs values < 1 for averaging
        filtered_y = y[y.abs() >= 1]
        avg = filtered_y.mean() if not filtered_y.empty else 0
        max_val = np.nanmax(np.abs(y))

        axs[i].plot(x, y, label=f"{axis}", linewidth=1.5)
        axs[i].axhline(avg, color='green', linestyle='--', label=f'Avg (|val|≥1): {avg:.2f}')
        axs[i].axhline(max_val, color='red', linestyle=':', label=f'Max: {max_val:.2f}')
        axs[i].axhline(-max_val, color='red', linestyle=':', alpha=0.5)
        axs[i].set_ylabel(f"{axis}", fontsize=10)
        axs[i].grid(True)
        axs[i].legend(fontsize=8)

    axs[-1].set_xlabel("Frame")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()

# ─────── Time Series Metrics ───────
def plot_metrics_subplot(df, frame_col):
    metrics = [
        ("X (Pixels)", "X Position (Pixels)"),
        ("Y (Pixels)", "Y Position (Pixels)"),
        ("Displacement (Microns)", "Displacement (µm)"),
        ("Velocity (Microns/s)", "Velocity Magnitude (µm/s)"),
        ("Acceleration (Microns/s²)", "Acceleration Magnitude (µm/s²)"),
    ]

    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Motion Metrics Over Time", fontsize=14)

    for i, (col, title) in enumerate(metrics):
        if col in df.columns:
            x = df[frame_col]
            y = df[col]

            filtered_y = y[y.abs() >= 1]
            avg = filtered_y.mean() if not filtered_y.empty else 0
            max_val = np.nanmax(y)

            axs[i].plot(x, y, label=col, linewidth=1.2)
            axs[i].axhline(avg, color='green', linestyle='--', label=f'Avg (|val|≥1): {avg:.2f}')
            axs[i].axhline(max_val, color='red', linestyle=':', label=f'Max: {max_val:.2f}')
            axs[i].set_ylabel(title, fontsize=9)
            axs[i].legend(fontsize=8)
            axs[i].grid(True)

    axs[-1].set_xlabel("Frame")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

# ─────── Separate Velocity and Acceleration (X and Y) ───────
def plot_velocity_acceleration_components(df, frame_col):
    import numpy as np
    import matplotlib.pyplot as plt

    metrics = [
        ("X Velocity (Microns/s)", "X Velocity (µm/s)"),
        ("Y Velocity (Microns/s)", "Y Velocity (µm/s)"),
        ("X Acceleration (Microns/s²)", "X Acceleration (µm/s²)"),
        ("Y Acceleration (Microns/s²)", "Y Acceleration (µm/s²)"),
    ]

    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 8), sharex=True)
    fig.suptitle("X and Y Velocity and Acceleration vs Time", fontsize=14)

    for i, (col, title) in enumerate(metrics):
        if col in df.columns:
            x = df[frame_col].to_numpy()
            y = df[col].to_numpy()

            # Find frames where abs(y) >= 1
            active_frames = x[np.abs(y) >= 1]

            if active_frames.size > 0:
                margin = 10
                xlim_min = max(active_frames.min() - margin, x.min())
                xlim_max = min(active_frames.max() + margin, x.max())
            else:
                # no significant movement, plot full range
                xlim_min, xlim_max = x.min(), x.max()

            # Compute average and max ignoring values with abs < 1
            filtered_y = y[np.abs(y) >= 1]
            avg = filtered_y.mean() if filtered_y.size > 0 else 0
            max_val = np.nanmax(np.abs(y))

            axs[i].plot(x, y, label=col, linewidth=1.2)
            axs[i].axhline(avg, color='green', linestyle='--', label=f'Avg (|val|≥1): {avg:.2f}')
            axs[i].axhline(max_val, color='red', linestyle=':', label=f'Max: {max_val:.2f}')
            axs[i].axhline(-max_val, color='red', linestyle=':', alpha=0.5)
            axs[i].set_xlim(xlim_min, xlim_max)
            axs[i].set_ylabel(title, fontsize=10)
            axs[i].legend(fontsize=8)
            axs[i].grid(True)

    axs[-1].set_xlabel("Frame")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


    

# ─────── Bode Plot ───────
def plot_bode_subplot(df, fps):
    signals = [
        ("Displacement (Microns)", "Displacement (µm)"),
        ("Velocity (Microns/s)", "Velocity (µm/s)"),
        ("Acceleration (Microns/s²)", "Acceleration (µm/s²)"),
    ]

    fig, axs = plt.subplots(len(signals), 2, figsize=(14, 8), sharex=False)
    fig.suptitle("Bode Plots – Magnitude & Phase", fontsize=14)

    for i, (col, label) in enumerate(signals):
        if col in df.columns:
            signal = df[col].replace(0, np.nan).ffill().fillna(0)
            n = len(signal)
            signal = signal - np.nanmean(signal)
            signal = np.nan_to_num(signal)

            yf = fft(signal)
            xf = fftfreq(n, 1 / fps)
            mask = xf > 0
            xf = xf[mask]
            yf = yf[mask]

            magnitude = 20 * np.log10(np.abs(yf))
            phase = np.angle(yf, deg=True)

            axs[i, 0].semilogx(xf, magnitude, color='tab:blue')
            axs[i, 0].set_ylabel("Mag (dB)", fontsize=9)
            axs[i, 0].set_title(f"{label} – Magnitude", fontsize=10)
            axs[i, 0].grid(True, which="both")

            axs[i, 1].semilogx(xf, phase, color='tab:orange')
            axs[i, 1].set_ylabel("Phase (°)", fontsize=9)
            axs[i, 1].set_title(f"{label} – Phase", fontsize=10)
            axs[i, 1].grid(True, which="both")

    for ax in axs[-1]:
        ax.set_xlabel("Frequency (Hz)")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()

# ─────── Main ───────
if __name__ == "__main__":
    path = select_csv_file()
    df = pd.read_csv(path)

    try:
        fps = float(df["FPS"].iloc[0])
    except:
        print("FPS not found — defaulting to 1")
        fps = 1

    frame_col = "Frame" 
    if frame_col not in df.columns:
        raise KeyError(f"Column '{frame_col}' not found in CSV")

    plot_xy_displacement(df, frame_col)
    plot_metrics_subplot(df, frame_col)
    plot_velocity_acceleration_components(df, frame_col)  # new plots for X/Y velocity & accel
    plot_bode_subplot(df, fps)
