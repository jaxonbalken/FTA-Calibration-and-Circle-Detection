import h5py
import cv2
import numpy as np
import os
import time
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Hide the root tkinter window
Tk().withdraw()

# Let the user choose a file
file_path = askopenfilename(
    title="Select HDF5 File",
    filetypes=[("HDF5 files", "*.h5 *.hdf5"), ("All files", "*.*")]
)

# Check if user selected a file
if not file_path:
    print("[ERROR] No file selected.")
    exit()

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

frame_count = len(frames)

# ==== Configuration ====
capture_fps = 120   # Original video capture rate (e.g., high-speed camera)
playback_fps = 30   # Desired slow-motion playback rate
slowdown_factor = capture_fps / playback_fps
delay = int(1000 / playback_fps)

# ==== Duration calculations ====
original_duration = frame_count / capture_fps
playback_duration = frame_count / playback_fps

print(f"[INFO] Loaded {frame_count} frames from: {os.path.basename(file_path)}")
print(f"[INFO] Original capture rate: {capture_fps} FPS")
print(f"[INFO] Intended playback rate: {playback_fps} FPS (Slow motion: {slowdown_factor:.1f}x)")
print(f"[INFO] Original video duration: {original_duration:.2f} seconds")
print(f"[INFO] Expected playback duration: {playback_duration:.2f} seconds")
print("Press 'q' to quit early.\n")

# Start playback timer
start_time = time.time()

# Playback loop
for i, frame in enumerate(frames):
    cv2.imshow("Slow Motion Playback - Press 'q' to quit", frame)
    
    key = cv2.waitKey(delay)
    if key == ord('q') or key == 27:  # 'q' or ESC to quit
        print("[INFO] Playback stopped by user.")
        break

end_time = time.time()
actual_duration = end_time - start_time
actual_fps = frame_count / actual_duration if actual_duration > 0 else 0

cv2.destroyAllWindows()

# Final stats
print("\n[INFO] Playback finished.")
print(f"[INFO] Actual playback time: {actual_duration:.2f} seconds")
print(f"[INFO] Actual FPS during playback: {actual_fps:.2f}")
print(f"[INFO] Slowdown factor (actual): {capture_fps / actual_fps:.2f}x")
