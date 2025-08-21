import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
import csv
import os

# Constant for pixel-to-micron conversion
MICRONS_PER_PIXEL = 2.27 #for FTA 5
#for FTA6 , MICRONS_PER_PIXEL = 125/54
def plot_centroid_y_microns():
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

    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    frame = int(row['Frame'])
                    y = row['Centroid_Y'].strip()

                    if y == '':
                        continue

                    y = float(y) * MICRONS_PER_PIXEL

                    frames.append(frame)
                    centroid_y_microns.append(y)

                except (KeyError, ValueError):
                    continue

        if not frames:
            print("No valid data found in CSV.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(frames, centroid_y_microns, marker='o', linestyle='-', color='blue')
        plt.xlabel("Frames")
        plt.ylabel("Centroid Y (μm)")
        plt.title("Centroid Y Position Over Time")
        plt.grid(True)
        plt.tight_layout()
        plt.suptitle(os.path.basename(file_path), fontsize=10, y=1.02)
        plt.show()

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    plot_centroid_y_microns()
