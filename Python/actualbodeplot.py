import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# --- Experimental Data --- first try with fta 5
freqs = np.array([1, 50, 100, 150, 200, 250, 275, 300, 325, 350, 400, 450, 500, 550, 575, 600])
displacements = np.array([42, 47, 59, 44, 55, 84, 95, 85, 61, 37, 24, 21, 17, 15, 13, 11])

# ----- second try at data ----- FTA 5
freqs2 = np.array([1,25,50,75,100,150,200,225,250,275,300,350,400,450,500,550,600])
displacements2 = np.array([57,52,52,53,52,66,89,77,108,137,173,116,65,42,35,22,18])

# ----- 3rd set of data ----- FTA 6
freqs2 = np.array([1,25,50,75,100,150,200,225,250,275,300,350,400,450,500,550,600])
displacements3 = np.array([59,48,48,50,49,57,68,75,93,84,125,137,78,46,35,24,18])


# Normalize gain
reference = max(displacements)
gain = displacements / reference

# --- Second-order magnitude model ---
def second_order_mag(f, K, fn, zeta):
    return K / np.sqrt((1 - (f / fn)**2)**2 + (2 * zeta * f / fn)**2)

# Fit model
p0 = [1.0, 275, 0.05]
popt, _ = curve_fit(second_order_mag, freqs, gain, p0=p0)
K_fit, fn_fit, zeta_fit = popt

# Generate smooth frequency curve
f_fit = np.linspace(min(freqs), max(freqs), 500)
gain_fit = second_order_mag(f_fit, *popt)
gain_fit_db = 20 * np.log10(gain_fit)
gain_db = 20 * np.log10(gain)

# --- Phase Model ---
def second_order_phase(f, fn, zeta):
    epsilon = 1e-9
    num = 2 * zeta * (f / fn)
    denom = 1 - (f / fn)**2 + epsilon
    phase_rad = -np.arctan2(num, denom)
    return np.degrees(phase_rad)

phase_fit_deg = second_order_phase(f_fit, fn_fit, zeta_fit)

# --- Find peak and lowest gain points ---
peak_idx = np.argmax(gain_fit_db)
dip_idx = np.argmin(gain_fit_db)
peak_freq = f_fit[peak_idx]
dip_freq = f_fit[dip_idx]
peak_gain = gain_fit_db[peak_idx]
dip_gain = gain_fit_db[dip_idx]

# --- Plotting ---
plt.figure(figsize=(10, 8))

# --- Magnitude Plot ---
plt.subplot(2, 1, 1)
plt.semilogx(freqs, gain_db, 'o', label='Measured')
plt.semilogx(f_fit, gain_fit_db, '-', label='Fitted')

# Vertical lines at peak and dip frequencies
plt.axvline(peak_freq, color='green', linestyle='--', label='Peak Frequency')
plt.axvline(dip_freq, color='red', linestyle='--', label='Min Frequency')

# Annotate peak and min gain coordinates on magnitude plot
plt.annotate(f"Peak:\n({peak_freq:.1f} Hz, {peak_gain:.1f} dB)",
             xy=(peak_freq, peak_gain),
             xytext=(peak_freq*1.1, peak_gain + 5),
             arrowprops=dict(facecolor='green', shrink=0.05),
             fontsize=10, color='green')

plt.annotate(f"Min:\n({dip_freq:.1f} Hz, {dip_gain:.1f} dB)",
             xy=(dip_freq, dip_gain),
             xytext=(dip_freq*0.8, dip_gain - 10),
             arrowprops=dict(facecolor='red', shrink=0.05),
             fontsize=10, color='red')

plt.ylabel("Magnitude (dB)")
plt.title("Bode Plot - Magnitude and Phase")
plt.grid(True, which='both', linestyle='--')
plt.legend()

# --- Phase Plot ---
plt.subplot(2, 1, 2)
plt.semilogx(f_fit, phase_fit_deg, '-', color='orange', label='Fitted Phase')

# Vertical lines aligned with magnitude plot
plt.axvline(peak_freq, color='green', linestyle='--', label='Peak Frequency')
plt.axvline(dip_freq, color='red', linestyle='--', label='Min Frequency')

plt.ylabel("Phase (degrees)")
plt.xlabel("Frequency (Hz)")
plt.grid(True, which='both', linestyle='--')
plt.legend()

plt.tight_layout()
plt.show()

# --- Print Fitted and Marked Info ---
print(f"Fitted Resonant Frequency (fn): {fn_fit:.2f} Hz")
print(f"Fitted Damping Ratio (zeta): {zeta_fit:.4f}")
print(f"Fitted Gain (K): {K_fit:.2f}")
print(f"\nPeak Gain: {peak_gain:.2f} dB at {peak_freq:.2f} Hz")
print(f"Min Gain: {dip_gain:.2f} dB at {dip_freq:.2f} Hz")
