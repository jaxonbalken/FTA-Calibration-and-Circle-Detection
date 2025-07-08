import h5py

file_path = r"C:\Users\ASE\Documents\GitHub\FTA-Calibration-and-Circle-Detection\SAVEDFRAMES.h5"

with h5py.File(file_path, 'r') as f:
    print("Keys (datasets/groups) in the file:", list(f.keys()))
    # Let's say you want to check the first key
    first_key = list(f.keys())[0]
    data = f[first_key][:]
    print(f"Data inside '{first_key}':")
    print(data)
