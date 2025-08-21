import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
import os

def analyze_motion_from_csv():
    # Constants
    MICRONS_PER_PIXEL = 2.083  # 125 micron fiber diameter / ~30 px radius * 2
    FPS = 5  # frames per second

    # Setup file dialog
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Centroid CSV File",
        filetypes=[("CSV Files", "*.csv")]
    )

    if not file_path or not os.path.exists(file_path):
        print("[ERROR] No file selected or file does not exist.")
        return

    try:
        df = pd.read_csv(file_path)

        # Convert 'None' to NaN
        df['Centroid_X'] = pd.to_numeric(df['Centroid_X'], errors='coerce')
        df['Centroid_Y'] = pd.to_numeric(df['Centroid_Y'], errors='coerce')

        # Drop rows with missing centroids
        df_valid = df.dropna(subset=['Centroid_X', 'Centroid_Y']).reset_index(drop=True)

        if df_valid.empty or len(df_valid) < 2:
            print("[ERROR] Not enough valid centroid data for motion analysis.")
            return

        # Convert pixel to microns
        x = df_valid['Centroid_X'].to_numpy() * MICRONS_PER_PIXEL
        y = df_valid['Centroid_Y'].to_numpy() * MICRONS_PER_PIXEL
        frames = df_valid['Frame'].to_numpy()

        # Compute displacement
        dx = np.diff(x)
        dy = np.diff(y)
        disp = np.sqrt(dx**2 + dy**2)

        # Velocity (µm/frame and µm/sec)
        velocity_per_frame = disp
        velocity_per_sec = velocity_per_frame * FPS

        # Acceleration (µm/frame² and µm/sec²)
        acc_per_frame2 = np.diff(velocity_per_frame)
        acc_per_sec2 = acc_per_frame2 * (FPS**2)

        # Max X/Y/total displacement
        max_dx = np.nanmax(x) - np.nanmin(x)
        max_dy = np.nanmax(y) - np.nanmin(y)
        total_disp = np.sqrt(max_dx**2 + max_dy**2)

        # Output results
        print("\n====== Micron-Scale Motion Analysis ======")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Microns per pixel: {MICRONS_PER_PIXEL}")
        print(f"Frame Rate: {FPS} fps\n")

        print("-- Displacement --")
        print(f"Max X displacement: {max_dx:.2f} µm")
        print(f"Max Y displacement: {max_dy:.2f} µm")
        print(f"Max total displacement: {total_disp:.2f} µm\n")

        print("-- Velocity --")
        print(f"Average velocity: {np.mean(velocity_per_frame):.2f} µm/frame | {np.mean(velocity_per_sec):.2f} µm/s")
        print(f"Max velocity: {np.max(velocity_per_frame):.2f} µm/frame | {np.max(velocity_per_sec):.2f} µm/s\n")

        print("-- Acceleration --")
        print(f"Max acceleration: {np.max(np.abs(acc_per_frame2)):.2f} µm/frame² | {np.max(np.abs(acc_per_sec2)):.2f} µm/s²")
        print("==========================================\n")

        # ======== PLOTTING ========
        plt.figure(figsize=(12, 5))

        # Plot X Position
        plt.subplot(1, 2, 1)
        plt.plot(frames, x, label="X Position", color="blue")
        plt.xlabel("Frame")
        plt.ylabel("X Position (µm)")
        plt.title("X Centroid Position Over Time")
        plt.grid(True)

        # Plot Y Position
        plt.subplot(1, 2, 2)
        plt.plot(frames, y, label="Y Position", color="green")
        plt.xlabel("Frame")
        plt.ylabel("Y Position (µm)")
        plt.title("Y Centroid Position Over Time")
        plt.grid(True)

        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"[ERROR] Failed to analyze motion: {e}")

if __name__ == "__main__":
    analyze_motion_from_csv()
