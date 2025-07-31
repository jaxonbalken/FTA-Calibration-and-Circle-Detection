import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
import csv
import os

# Constant for pixel-to-micron conversion
MICRONS_PER_PIXEL = 2.27

def plot_centroid_y_and_dy_microns():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:
        print("No file selected.")
        return

    frames = []
    centroid_y_microns = []
    abs_dy_microns = []

    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    frame = int(row['Frame'])
                    y = row['Centroid_Y'].strip()
                    dy = row['Movement_Y (dY)'].strip()

                    if y == '' or dy == '':
                        continue

                    y = float(y) * MICRONS_PER_PIXEL
                    dy = abs(float(dy)) * MICRONS_PER_PIXEL

                    frames.append(frame)
                    centroid_y_microns.append(y)
                    abs_dy_microns.append(dy)

                except (KeyError, ValueError):
                    continue

        if not frames:
            print("No valid data found in CSV.")
            return

        max_dy = max(abs_dy_microns)
        threshold = 10 * MICRONS_PER_PIXEL  # Optional: convert pixel threshold to microns (22.7)

        fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

        # Centroid Y (in microns)
        axs[0].plot(frames, centroid_y_microns, marker='o', linestyle='-', color='blue')
        axs[0].set_ylabel("Centroid Y (μm)")
        axs[0].set_title("Centroid Y Position Over Time")
        axs[0].grid(True)

        # Bode Plot for |ΔY| (in microns)
        axs[1].plot(frames, abs_dy_microns, marker='x', linestyle='-', color='green', label='|ΔY| (μm)')
        axs[1].axhline(y=max_dy, color='red', linestyle='--', linewidth=1,
                       label=f'Max |ΔY| = {max_dy:.2f} μm')
        axs[1].axhline(y=threshold, color='orange', linestyle=':', linewidth=1,
                       label=f'Minimum = {threshold:.2f} μm')

        axs[1].set_xlabel("Frame")
        axs[1].set_ylabel("|ΔY| (μm)")
        axs[1].set_title("Y Displacement (|ΔY| in μm)")
        axs[1].grid(True)
        axs[1].legend()

        plt.tight_layout()
        plt.suptitle(os.path.basename(file_path), fontsize=10, y=1.02)
        plt.show()

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    plot_centroid_y_and_dy_microns()
