import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
import csv

def plot_centroid_y_from_csv():
    # Use tkinter to open file dialog
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:
        print("No file selected.")
        return

    frames = []
    centroid_y = []

    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    frame = int(row['Frame'])
                    y = row['Centroid_Y'].strip()
                    if y == '':
                        continue  # Skip missing values
                    y = float(y)
                    frames.append(frame)
                    centroid_y.append(y)
                except (KeyError, ValueError) as e:
                    # Skip rows with missing or non-numeric data
                    continue

        if not frames or not centroid_y:
            print("No valid centroid data found.")
            return

        # Plot
        plt.figure(figsize=(10, 5))
        plt.plot(frames, centroid_y, marker='o', linestyle='-', color='b')
        plt.title('Centroid Y Position vs Frame')
        plt.xlabel('Frame')
        plt.ylabel('Centroid Y')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Error reading or plotting CSV: {e}")

if __name__ == "__main__":
    plot_centroid_y_from_csv()
