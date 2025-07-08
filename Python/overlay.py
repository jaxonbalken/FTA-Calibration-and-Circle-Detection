import cv2
import numpy as np
import pandas as pd
import h5py
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

def load_h5_video(h5_path):
    """Load video frames from .h5 file (assuming frames stored as dataset 'frames')."""
    with h5py.File(h5_path, 'r') as f:
        frames = f['frames'][:]  # shape: (num_frames, H, W) or (num_frames, H, W, C)
        if len(frames.shape) == 3:  # grayscale
            frames = np.stack([frames]*3, axis=-1)
    return frames

def load_centroids(csv_path):
    df = pd.read_csv(csv_path)
    print("CSV columns found:", df.columns.tolist())
    if 'Centroid_X' not in df.columns or 'Centroid_Y' not in df.columns:
        raise ValueError("CSV file must contain 'Centroid_X' and 'Centroid_Y' columns")
    return df[['Centroid_X', 'Centroid_Y']].values

def get_trail_colors(length):
    """Generate color gradient from red to blue for trail points."""
    colors = []
    for i in range(length):
        r = int(255 * (1 - i / max(1, length - 1)))
        g = 0
        b = int(255 * (i / max(1, length - 1)))
        colors.append((b, g, r))  # OpenCV uses BGR
    return colors

def main():
    Tk().withdraw()

    print("Select the .h5 video file")
    h5_path = askopenfilename(filetypes=[("H5 files", "*.h5")])
    if not h5_path:
        print("No .h5 file selected, exiting.")
        return

    print("Select the corresponding centroid .csv file")
    csv_path = askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not csv_path:
        print("No .csv file selected, exiting.")
        return

    print("Loading video frames...")
    frames = load_h5_video(h5_path)
    print(f"Loaded {len(frames)} frames.")

    print("Loading centroid data...")
    centroids = load_centroids(csv_path)
    print(f"Loaded {len(centroids)} centroid points.")

    if len(centroids) != len(frames):
        print("Warning: Number of centroids and frames differ. Will overlay up to the minimum count.")

    save_path = asksaveasfilename(defaultextension=".mp4",
                                   filetypes=[("MP4 files", "*.mp4")],
                                   title="Save new video as")
    if not save_path:
        print("No save path selected, exiting.")
        return

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 5
    out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

    frame_count = min(len(frames), len(centroids))
    trail_buffer = []

    for i in range(frame_count):
        frame = frames[i].copy()
        cx_raw, cy_raw = centroids[i]
        cx_str, cy_str = str(cx_raw), str(cy_raw)

        # Valid centroid check
        if cx_str != 'None' and cy_str != 'None':
            try:
                cx, cy = int(float(cx_str)), int(float(cy_str))
                trail_buffer.append((cx, cy))  # update trail
            except ValueError:
                pass  # skip invalid conversion

        # Draw persistent trail (all valid points so far)
        trail_colors = get_trail_colors(len(trail_buffer))
        for idx, (x, y) in enumerate(trail_buffer):
            cv2.circle(frame, (x, y), 3, trail_colors[idx], -1)

        out.write(frame)

    out.release()
    print(f"Video saved successfully at: {save_path}")

if __name__ == "__main__":
    main()
