import cv2
import numpy as np
import pandas as pd
import h5py
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

def load_h5_video(h5_path):
    """Load video frames from .h5 file (assuming frames stored as dataset 'frames')."""
    with h5py.File(h5_path, 'r') as f:
        # You may need to change the dataset name based on your file
        frames = f['frames'][:]  # shape: (num_frames, height, width, channels) or grayscale (num_frames, height, width)
        # Convert grayscale to BGR if needed
        if len(frames.shape) == 3:  # grayscale video
            frames = np.stack([frames]*3, axis=-1)
    return frames

def load_centroids(csv_path):
    df = pd.read_csv(csv_path)
    print("CSV columns found:", df.columns.tolist())  # for debug
    if 'Centroid_X' not in df.columns or 'Centroid_Y' not in df.columns:
        raise ValueError("CSV file must contain 'Centroid_X' and 'Centroid_Y' columns")
    centroids = df[['Centroid_X', 'Centroid_Y']].values
    return centroids
def main():
    Tk().withdraw()  # Hide the root Tk window
    
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
    
    # Setup video writer
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    save_path = asksaveasfilename(defaultextension=".mp4",
                                  filetypes=[("MP4 files", "*.mp4")],
                                  title="Save new video as")
    if not save_path:
        print("No save path selected, exiting.")
        return
    
    # Assuming 30 fps, change if you want or read from metadata if available
    fps = 30
    out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))
    
    frame_count = min(len(frames), len(centroids))
    for i in range(frame_count):
        frame = frames[i].copy()
        
        # Overlay centroid
        cx, cy = int(centroids[i][0]), int(centroids[i][1])
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)  # red circle
        
        out.write(frame)
    
    out.release()
    print(f"Video saved successfully at: {save_path}")

if __name__ == "__main__":
    main()
