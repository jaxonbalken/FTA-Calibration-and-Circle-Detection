import re
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from tkinter import Tk, filedialog

# ─────────────────────── file selection popup ───────────────────────
def select_file(title, filetypes):
    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    if not path:
        raise FileNotFoundError("File selection cancelled.")
    return Path(path)

TXT_PATH = select_file("Select FireCapture TXT file", [("Text files", "*.txt")])
AVI_PATH = select_file("Select AVI video file", [("AVI files", "*.avi")])
OUT_CSV  = AVI_PATH.with_suffix(".combined.csv")

# ─────────────────── 1. read metadata txt ──────────────────
def read_firecapture_txt(path: Path) -> dict:
    patterns = {
        "date"            : r"^Date=",
        "duration"        : r"^Duration=",
        "frames_captured" : r"^Frames captured=",
        "fps"             : r"^FPS \(avg\.\)=",
        "roi"             : r"^ROI=",
        "shutter"         : r"^Shutter=",
        "gain"            : r"^Gain=",
    }
    meta = {}
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc) as f:
                for line in f:
                    for key, pat in patterns.items():
                        if re.match(pat, line):
                            meta[key] = line.split("=", 1)[1].strip()
            break
        except UnicodeDecodeError:
            continue
    return meta

meta = read_firecapture_txt(TXT_PATH)
print("Parsed FireCapture fields:", meta)

# Fixed radius in pixels (given)
FIXED_RADIUS_PIXELS = 14
# Known physical radius of fiber tip in microns
FIBER_TIP_RADIUS_MICRONS = 125 / 2

# Calculate microns per pixel using fixed radius
microns_per_pixel = FIBER_TIP_RADIUS_MICRONS / FIXED_RADIUS_PIXELS
print(f"Using fixed radius: {FIXED_RADIUS_PIXELS} pixels")
print(f"Calculated microns per pixel: {microns_per_pixel:.4f}")

# ───────────────── 2. per-frame centroid extraction ─────────────────
def frame_centroid(gray: np.ndarray):
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, mask, None
    cnt = max(cnts, key=cv2.contourArea)
    M = cv2.moments(cnt)
    if M["m00"] == 0:
        return None, mask, cnt
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return (cx, cy), mask, cnt

cap = cv2.VideoCapture(str(AVI_PATH))
if not cap.isOpened():
    raise FileNotFoundError(f"Cannot open {AVI_PATH}")

n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
records  = []

preview = True  # Show centroid overlay

with tqdm(total=n_frames, desc="Centroids") as bar:
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        c, mask, cnt = frame_centroid(gray)
        if c is not None:
            records.append((idx, *c, FIXED_RADIUS_PIXELS))
            if preview:
                cx, cy = map(int, c)
                cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 1)
                cv2.circle(frame, (cx, cy), FIXED_RADIUS_PIXELS, (255, 0, 0), 1)
        else:
            records.append((idx, np.nan, np.nan, FIXED_RADIUS_PIXELS))

        if preview:
            cv2.imshow("Centroid Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                preview = False
                cv2.destroyWindow("Centroid Preview")

        idx += 1
        bar.update()
cap.release()
cv2.destroyAllWindows()

df = pd.DataFrame(records, columns=["frame", "x", "y", "radius"])

# ─────────────── 3. displacement, velocity, acceleration in pixels ───────────────
fps = float(meta.get("fps", 1))  # fallback to 1 if not available
dt = 1 / fps

first = df.dropna(subset=['x', 'y']).iloc[0][["x", "y"]].to_numpy()
df["dx"] = df["x"] - first[0]
df["dy"] = df["y"] - first[1]
df["displacement"] = np.sqrt(df["dx"]**2 + df["dy"]**2)

df["vx"] = df["x"].diff() / dt
df["vy"] = df["y"].diff() / dt
df["velocity"] = np.sqrt(df["vx"]**2 + df["vy"]**2)

df["ax"] = df["vx"].diff() / dt
df["ay"] = df["vy"].diff() / dt
df["acceleration"] = np.sqrt(df["ax"]**2 + df["ay"]**2)

# ─────────────── 4. convert to microns using microns per pixel ───────────────
df["Microns per Pixel"] = microns_per_pixel

df["dx (Microns)"] = df["dx"] * microns_per_pixel
df["dy (Microns)"] = df["dy"] * microns_per_pixel
df["Displacement (Microns)"] = df["displacement"] * microns_per_pixel

df["vx (Microns/s)"] = df["vx"] * microns_per_pixel
df["vy (Microns/s)"] = df["vy"] * microns_per_pixel
df["Velocity (Microns/s)"] = df["velocity"] * microns_per_pixel

df["ax (Microns/s²)"] = df["ax"] * microns_per_pixel
df["ay (Microns/s²)"] = df["ay"] * microns_per_pixel
df["Acceleration (Microns/s²)"] = df["acceleration"] * microns_per_pixel

df["Radius (Microns)"] = df["radius"] * microns_per_pixel

# ─────────────── 5. attach metadata ───────────────
for key in ["fps", "date", "duration", "frames_captured", "roi", "shutter", "gain"]:
    df[key] = meta.get(key, "NA")

# ─────────────── 6. format headers + save ───────────────
ordered = [
    "frame", "x", "y", "radius", "Radius (Microns)", "Microns per Pixel",
    "dx", "dy", "dx (Microns)", "dy (Microns)",
    "displacement", "Displacement (Microns)",
    "vx", "vy", "vx (Microns/s)", "vy (Microns/s)",
    "velocity", "Velocity (Microns/s)",
    "ax", "ay", "ax (Microns/s²)", "ay (Microns/s²)",
    "acceleration", "Acceleration (Microns/s²)",
    "fps", "date", "duration", "frames_captured", "roi", "shutter", "gain"
]
df = df[ordered]

column_labels = {
    "frame": "Frame",
    "x": "X (Pixels)", "y": "Y (Pixels)",
    "radius": "Radius (Pixels)", "Radius (Microns)": "Radius (Microns)",
    "Microns per Pixel": "Microns per Pixel",
    "dx": "dX (Pixels)", "dy": "dY (Pixels)",
    "dx (Microns)": "dX (Microns)", "dy (Microns)": "dY (Microns)",
    "displacement": "Displacement (Pixels)", "Displacement (Microns)": "Displacement (Microns)",
    "vx": "X Velocity (Pixels/s)", "vy": "Y Velocity (Pixels/s)",
    "vx (Microns/s)": "X Velocity (Microns/s)", "vy (Microns/s)": "Y Velocity (Microns/s)",
    "velocity": "Velocity (Pixels/s)", "Velocity (Microns/s)": "Velocity (Microns/s)",
    "ax": "X Acceleration (Pixels/s²)", "ay": "Y Acceleration (Pixels/s²)",
    "ax (Microns/s²)": "X Acceleration (Microns/s²)", "ay (Microns/s²)": "Y Acceleration (Microns/s²)",
    "acceleration": "Acceleration (Pixels/s²)", "Acceleration (Microns/s²)": "Acceleration (Microns/s²)",
    "fps": "FPS", "date": "Date", "duration": "Duration",
    "frames_captured": "Frames Captured",
    "roi": "ROI", "shutter": "Shutter", "gain": "Gain"
}
df.columns = [column_labels.get(col, col.capitalize()) for col in df.columns]

df.to_csv(OUT_CSV, index=False)
print(f"\nCombined CSV saved ➜  {OUT_CSV}")
print(df.head())
