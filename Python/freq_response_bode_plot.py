import numpy as np
import matplotlib.pyplot as plt

# --- Experimental Data ---

# # First try with FTA 5
# freqs1 = np.array([1, 50, 100, 150, 200, 250, 275, 300, 325, 350, 400, 450, 500, 550, 575, 600])
# displacements1 = np.array([42, 47, 59, 44, 55, 84, 95, 85, 61, 37, 24, 21, 17, 15, 13, 11])

# Second try with FTA 5
freqs2 = np.array([1, 25, 50, 75, 100, 150, 200, 225, 250, 275, 300, 350, 400, 450, 500, 550, 600, 625, 650, 675, 700, 725, 750])
displacements2 = np.array([57, 52, 52, 53, 52, 66, 89, 77, 108, 137, 173, 116, 65, 42, 35, 22, 18, 16, 11, 12, 12, 10, 10])

# Third set (FTA 6)
displacements3 = np.array([59, 48, 48, 50, 49, 57, 68, 75, 93, 84, 125, 137, 78, 46, 35, 24, 18, 19, 14, 13, 11, 11, 11])

# --- Plotting ---

plt.figure(figsize=(12, 6))

# Plot each dataset
#plt.plot(freqs1, displacements1, marker='o', label='FTA 5 - Trial 1')
plt.plot(freqs2, displacements2, marker='s', label='FTA 5')
plt.plot(freqs2, displacements3, marker='^', label='FTA 6')

# --- Peaks and Minimums ---

# # FTA 5 - Trial 1
# peak_idx1 = np.argmax(displacements1)
# min_idx1 = np.argmin(displacements1)
# plt.axvline(freqs1[peak_idx1], linestyle='--', color='blue', alpha=0.3)
# plt.axvline(freqs1[min_idx1], linestyle='--', color='blue', alpha=0.15)
# plt.text(freqs1[peak_idx1], displacements1[peak_idx1] + 5,
#          f'↑ {freqs1[peak_idx1]} Hz', color='blue', fontsize=9)
# plt.text(freqs1[min_idx1], displacements1[min_idx1] - 5,
#          f'↓ {freqs1[min_idx1]} Hz', color='blue', fontsize=9)


# # --- Fit Polynomial Curves ---
# poly_order = 4  # 4th-degree polynomial

# # Fit and evaluate for FTA 5 - Trial 2
# coeffs2 = np.polyfit(freqs2, displacements2, poly_order)
# fit_curve2 = np.poly1d(coeffs2)
# fit_displacements2 = fit_curve2(freqs2)

# # Fit and evaluate for FTA 6
# coeffs3 = np.polyfit(freqs2, displacements3, poly_order)
# fit_curve3 = np.poly1d(coeffs3)
# fit_displacements3 = fit_curve3(freqs2)

# # Best-fit curves
# plt.plot(freqs2, fit_displacements2, linestyle='--', color='orange', alpha=0.6, label='Fit: FTA 5')
# plt.plot(freqs2, fit_displacements3, linestyle='--', color='green', alpha=0.6, label='Fit: FTA 6')



# FTA 5 - Trial 2
peak_idx2 = np.argmax(displacements2)
min_idx2 = np.argmin(displacements2)
plt.axvline(freqs2[peak_idx2], linestyle='--', color='orange', alpha=0.3)
plt.axvline(freqs2[min_idx2], linestyle='--', color='orange', alpha=0.15)
plt.text(freqs2[peak_idx2], displacements2[peak_idx2] + 1,
         f'↑ {freqs2[peak_idx2]} Hz', color='orange', fontsize=9)
plt.text(freqs2[min_idx2], displacements2[min_idx2] + 5,
         f'↓ {freqs2[min_idx2]} Hz', color='orange', fontsize=9)

# FTA 6
peak_idx3 = np.argmax(displacements3)
min_idx3 = np.argmin(displacements3)
plt.axvline(freqs2[peak_idx3], linestyle='--', color='green', alpha=0.3)
plt.axvline(freqs2[min_idx3], linestyle='--', color='green', alpha=0.15)
plt.text(freqs2[peak_idx3], displacements3[peak_idx3] + 5,
         f'↑ {freqs2[peak_idx3]} Hz', color='green', fontsize=9)
plt.text(freqs2[min_idx3], displacements3[min_idx3] - 7,
         f'↓ {freqs2[min_idx3]} Hz', color='green', fontsize=9)

# --- Final touches ---
plt.title("Frequency Response of FTAs")
plt.xlabel("Driving Frequency (Hz)")
plt.ylabel("Displacement (μm)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
