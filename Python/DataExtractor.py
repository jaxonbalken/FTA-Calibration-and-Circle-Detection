import re
from pathlib import Path
# --- path to the FireCapture settings log ---------------------
logfile = Path(r"C:\Users\ASE\Documents\GitHub\FTA-Calibration-and-Circle-Detection\MP4 Files\Test\030725\2025-07-03-1713_0-U-L-Test.txt")
# --- keys to harvest : {label_in_output : regex that matches the line} -------
patterns = {
    "Date"            : r"^Date=",
    "Duration"        : r"^Duration=",
    "Frames captured" : r"^Frames captured=",
    "FPS"             : r"^FPS \(avg\.\)=",
    "ROI"             : r"^ROI=",
    "Shutter"         : r"^Shutter=",
    "Gain"            : r"^Gain=",
}
results = {}
with logfile.open(encoding="windows-1252") as f:
    for line in f:
        for label, pat in patterns.items():
            if re.match(pat, line):
                # keep everything after the first “=” and strip whitespace
                results[label] = line.split("=", 1)[1].strip()
                break  # stop checking other patterns for this line
# --- pretty-print (or use the dict programmatically) -------------------------
for k in patterns:
    print(f"{k:17s}: {results.get(k, 'NOT FOUND')}")