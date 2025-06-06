import h5py
import cv2
import numpy as np
import os

# Path to your HDF5 file
file_path = r"C:\Users\ASE\Documents\GitHub\FTA-Calibration-and-Circle-Detection\SAVEDFRAMES.h5"

# Check if file exists
if not os.path.exists(file_path):
    print(f"[ERROR] File not found: {file_path}")
    exit()

# Load frames from the HDF5 file
with h5py.File(file_path, 'r') as f:
    if 'frames' not in f:
        print("[ERROR] 'frames' dataset not found in file.")
        exit()
    frames = f['frames'][:]

print(f"[INFO] Loaded {len(frames)} frames from file.")

# Playback settings
fps = 30  # Change this if you want faster/slower playback
delay = int(1000 / fps)  # Time between frames in ms

# Playback loop
for i, frame in enumerate(frames):
    cv2.imshow("Saved Video Playback - Press 'q' to quit", frame)
    
    key = cv2.waitKey(delay)
    if key == ord('q') or key == 27:  # 'q' or ESC to quit
        print("[INFO] Playback stopped by user.")
        break

cv2.destroyAllWindows()
print("[INFO] Playback finished.")
