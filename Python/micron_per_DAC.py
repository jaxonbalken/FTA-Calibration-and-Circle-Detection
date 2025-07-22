import os
import sys
import time
import csv
import ctypes
import traceback
import ctypes.wintypes
from tkinter import filedialog, messagebox
import tkinter as tk

import serial
import serial.tools.list_ports
import numpy as np
import cv2

import zwoasi as asi
import h5py

from PIL import Image, ImageTk

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.animation as animation
import matplotlib.cm as cm
import threading


class TestingApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Live Video Feed")

        self.serial = None
        self.port_name = None

        self.streaming = False
        self.camera_initialized = False
        self.roi_info_logged = False
        self.camera = None
        self.current_roi = (0, 0, 1936, 1096)  # Default full-frame ROI

        self.button_frame = tk.Frame(master)
        self.button_frame.pack(pady=10)

        # Gain input
        self.gain_label = tk.Label(master, text="Gain:")
        self.gain_label.pack()
        self.gain_entry = tk.Entry(master)
        self.gain_entry.insert(0, "0")
        self.gain_entry.pack()

        # Exposure input
        self.exposure_label = tk.Label(master, text="Exposure (µs):")
        self.exposure_label.pack()
        self.exposure_entry = tk.Entry(master)
        self.exposure_entry.insert(0, "30000")
        self.exposure_entry.pack()

        # ROI input
        self.roi_label = tk.Label(master, text="ROI (x, y, width, height):")
        self.roi_label.pack()
        self.roi_entry = tk.Entry(master)
        self.roi_entry.insert(0, "0, 0, 1936, 1096")
        self.roi_entry.pack()

        # DAC X and Y input
        self.dacx_label = tk.Label(master, text='X DAC')
        self.dacx_label.pack()
        self.dacx_entry = tk.Entry(master)
        self.dacx_entry.insert(2048, '2048')
        self.dacx_entry.pack()

        self.dacy_label = tk.Label(master, text='Y DAC')
        self.dacy_label.pack()
        self.dacy_entry = tk.Entry(master)
        self.dacy_entry.insert(2048, '2048')
        self.dacy_entry.pack()


        # Control buttons
        self.connect_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.serial_button = tk.Button(self.button_frame, text="Connect Serial", command=self.connect_serial)
        self.serial_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.amp_enable_button = tk.Button(self.button_frame, text="AMP Enable", command=self.amp_enable)
        self.amp_enable_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.amp_disable_button = tk.Button(self.button_frame, text="AMP Disable", command=self.amp_disable)
        self.amp_disable_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.start_button = tk.Button(self.button_frame, text="Start Feed", command=self.start_feed)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop Feed", command=self.stop_feed, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.play_button = tk.Button(self.button_frame, text="Play Saved Video", command=self.play_saved_video)
        self.play_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.analyze_button = tk.Button(self.button_frame, text="Analyze Centroids", command=self.analyze_saved_centroids)
        self.analyze_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.automate_button = tk.Button(self.button_frame, text='Start Automation', command=self.start_automation)
        self.automate_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.savedac_button = tk.Button(self.button_frame, text="Set DAC Values", command=self.set_dac_from_gui)
        self.savedac_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.dacx_scan_button = tk.Button(self.button_frame, text="Run DAC X Scan", command=self.start_dacx_scan)
        self.dacx_scan_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.dacy_scan_button = tk.Button(self.button_frame, text="Run DAC Y Scan", command=self.start_dacy_scan)
        self.dacy_scan_button.pack(side=tk.LEFT, padx=5, pady=5)


        tk.Button(master, text="Find Centroid", command=self.find_centroid_in_current_frame).pack(pady=5)

        self.video_frame = tk.Label(master)
        self.video_frame.pack()

    # ---- Serial Communication Functions ----

    def connect_serial(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            try:
                self.serial = serial.Serial(p.device, baudrate=115200, timeout=1)
                self.port_name = p.device
                print(f"✓ Connected to {p.device}")
                messagebox.showinfo("Serial Connected", f"Connected to {p.device}")
                return
            except Exception as e:
                print(f"❌ Failed to connect to {p.device}: {e}")
        messagebox.showerror("Connection Error", "Could not connect to any serial port.")

    def send(self, text):
        if self.serial and self.serial.is_open:
            print(f'to {self.port_name}: {text}')
            self.serial.write((text + '\n').encode('utf-8'))
        else:
            print("Serial not connected")

    def read_response(self):
        if self.serial and self.serial.in_waiting > 0:
            line = self.serial.readline()
            print(f'From {self.port_name}: {line}')
            return line.decode().strip()
        return ""

    def set_xy(self, x, y):
        self.send(f"set_x {x}")
        self.read_response()
        self.send(f"set_y {y}")
        self.read_response()

    def set_dac_from_gui(self):
        try:
            x = int(self.dacx_entry.get())
            y = int(self.dacy_entry.get())
            self.set_xy(x, y)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integer values for DAC X and Y.")

    def amp_enable(self):
        self.send("amp_enable")
        self.read_response()

    def amp_disable(self):
        self.send("amp_disable")
        self.read_response()

    def stop(self):
        self.send("stop")
        self.read_response()

    # ---- ROI Input Parser ----

    def update_current_roi_from_ui(self):
        try:
            x, y, w, h = map(int, self.roi_entry.get().split(','))
            self.current_roi = (x, y, w, h)
        except Exception as e:
            messagebox.showerror("ROI Error", f"Invalid ROI format: {e}")

    # ---- Camera Functions ----

    def connect_camera(self):
        print("Camera connection starting")
        try:
            asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll')
            num_cameras = asi.get_num_cameras()
            if num_cameras == 0:
                messagebox.showerror("Error", "No cameras found.")
                self.master.destroy()
                return
        
            self.camera = asi.Camera(0)
            self.camera.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1)
            self.camera.set_image_type(asi.ASI_IMG_RAW8)
            self.camera.set_roi(width=1936, height=1096) 
            

            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

            self.camera_initialized = True
            print("Camera Ready")
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))

    def start_dacx_scan(self):
        threading.Thread(target=self.run_dacx_scan, daemon=True).start()

    def start_dacy_scan(self):
        threading.Thread(target=self.run_dacy_scan, daemon=True).start()


    def start_feed(self):
        print("Starting Feed")
        if not self.camera_initialized:
            messagebox.showerror("Error", "Camera is not connected.")
            return
        self.stream_start_time = time.time()

        try:
            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for gain and exposure.")
            return

        try:
            self.update_current_roi_from_ui()
            x, y, w, h = self.current_roi
            self.camera.set_roi(start_x=x, start_y=y, width=w, height=h)
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

            self.camera.start_video_capture()
            self.streaming = True
            self.live_captured_frames = []
            self.stop_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.DISABLED)
            self.update_feed()
        except Exception as e:
            messagebox.showerror("Capture Failed", str(e))

    def stop_feed(self):
        print("Stopping Feed")
        if self.stream_start_time:
            duration = time.time() - self.stream_start_time
            print(f"[INFO] Video feed duration: {duration:.2f} seconds")
            self.stream_start_time = None
        if self.streaming:
            try:
                self.camera.stop_video_capture()
                self.streaming = False
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                print("Video feed stopped.")
            except Exception as e:
                messagebox.showerror("Stop Failed", str(e))

    def update_feed(self):
        if not self.streaming:
            return

        try:
            width, height, _, _ = self.camera.get_roi_format()
            if not self.roi_info_logged:
                print(f"[INFO] ROI Format: width={width}, height={height}")
                self.roi_info_logged = True

            expected_buffer_size = width * height
            buffer = bytearray(expected_buffer_size)

            self.camera.get_video_data(1000, buffer)

            frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width))
            frame_resized = cv2.resize(frame, (640, 480))

            if not hasattr(self, 'live_captured_frames'):
                self.live_captured_frames = []
            self.live_captured_frames.append(frame.copy())
            if len(self.live_captured_frames) > 5000:
                self.live_captured_frames.pop(0)

            img = Image.fromarray(frame_resized, mode='L')
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_frame.configure(image=imgtk)
            self.video_frame.image = imgtk
            self.master.after(1, self.update_feed)

        except Exception as e:
            print("\n[ERROR] Live feed failed.")
            print(f"Message: {e}")
            traceback.print_exc()
            print("[INFO] Stopping video feed...\n")
            return

    def on_close(self):
        if self.streaming:
            self.stop_feed()
        self.master.destroy()
        

    def start_automation(self):
    # Run the automation in a separate thread so the GUI stays responsive
        threading.Thread(target=self.automate_scan, daemon=True).start()

    def automate_scan(self):
        if not self.serial or not self.serial.is_open:
            messagebox.showerror("Error", "Serial port not connected.")
            return
        if not self.streaming:
            messagebox.showerror("Error", "Start the camera feed first.")
            return

        results = []
        fixed_radius = 27.12  # Fixed radius in pixels
        actual_radius_microns = 125
        pixel_to_micron_scale = actual_radius_microns / fixed_radius

        # ---- X DAC Scan (Y fixed) ----
        fixed_dacy = 2048
        print("Starting DAC X scan...")
        previous_centroid = None

        for dacx in range(500, 3001, 100):
            self.set_xy(dacx, fixed_dacy)
            time.sleep(3)

            centroid, _ = self.find_centroid_in_current_frame()
            dx_pix = dy_pix = dx_um = dy_um = ''
            microns_per_dac_x = microns_per_dac_y = ''

            if centroid is not None:
                cx, cy = centroid
                if previous_centroid is not None:
                    dx_pix = cx - previous_centroid[0]
                    dy_pix = cy - previous_centroid[1]
                    dx_um = dx_pix * pixel_to_micron_scale
                    dy_um = dy_pix * pixel_to_micron_scale
                    microns_per_dac_x = abs(dx_um / 100)
                    microns_per_dac_y = abs(dy_um / 100)

                previous_centroid = (cx, cy)
            else:
                cx = cy = ''

            results.append([
                dacx, fixed_dacy, cx, cy, fixed_radius,
                dx_pix, dy_pix, dx_um, dy_um,
                microns_per_dac_x, microns_per_dac_y
            ])

        # ---- Y DAC Scan (X fixed) ----
        fixed_dacx = 2048
        print("Starting DAC Y scan...")
        self.set_xy(2048, 2048)
        time.sleep(10)
        previous_centroid = None

        for dacy in range(500, 3001, 100):
            self.set_xy(fixed_dacx, dacy)
            time.sleep(3)

            centroid, _ = self.find_centroid_in_current_frame()
            dx_pix = dy_pix = dx_um = dy_um = ''
            microns_per_dac_x = microns_per_dac_y = ''

            if centroid is not None:
                cx, cy = centroid
                if previous_centroid is not None:
                    dx_pix = cx - previous_centroid[0]
                    dy_pix = cy - previous_centroid[1]
                    dx_um = dx_pix * pixel_to_micron_scale
                    dy_um = dy_pix * pixel_to_micron_scale
                    microns_per_dac_x = abs(dx_um / 100)
                    microns_per_dac_y = abs(dy_um / 100)

                previous_centroid = (cx, cy)
            else:
                cx = cy = ''

            results.append([
                fixed_dacx, dacy, cx, cy, fixed_radius,
                dx_pix, dy_pix, dx_um, dy_um,
                microns_per_dac_x, microns_per_dac_y
            ])

        # ---- Save to CSV ----
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv")],
                                                title="Save Automation Results")
        if filename:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'DAC_X', 'DAC_Y', 'Centroid_X', 'Centroid_Y', 'Fixed_Radius_px',
                    'Delta_X_pixels', 'Delta_Y_pixels', 'Delta_X_microns', 'Delta_Y_microns',
                    'Microns/DAC_X', 'Microns/DAC_Y'
                ])
                for row in results:
                    writer.writerow(row)
            messagebox.showinfo("Save Complete", f"Results saved to {filename}")

        # ---- Final µm/ADC Step Stats ----
        dx_um_values = [row[7] for row in results if isinstance(row[7], (int, float, np.float64))]
        dy_um_values = [row[8] for row in results if isinstance(row[8], (int, float, np.float64))]

        if dx_um_values:
            avg_dx_um_per_adc = np.mean([abs(v) for v in dx_um_values]) / 100
            print(f"Avg µm/DAC step (X): {avg_dx_um_per_adc:.3f}")

        if dy_um_values:
            avg_dy_um_per_adc = np.mean([abs(v) for v in dy_um_values]) / 100
            print(f"Avg µm/DAC step (Y): {avg_dy_um_per_adc:.3f}")

        print("Automation complete.")

    
    def save_last_frames(self):
        print("Save frames placeholder")

    def play_saved_video(self):
        print("Play video placeholder")

    def analyze_saved_centroids(self):
        print("Analyze centroids placeholder")

    def find_centroid_in_current_frame(self):
        # Ensure we have a captured frame to analyze
        if not hasattr(self, 'live_captured_frames') or not self.live_captured_frames:
            print("No frames available to find centroid.")
            return None, None

        frame = self.live_captured_frames[-1]

        # Threshold the image (assumes bright object on dark background)
        _, thresh = cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("No contours found.")
            return None, None

        # Choose largest contour (assumed to be the object)
        largest_contour = max(contours, key=cv2.contourArea)

        # Compute centroid from image moments
        moments = cv2.moments(largest_contour)
        if moments["m00"] == 0:
            print("Zero contour area; centroid undefined.")
            return None, None

        cX = int(moments["m10"] / moments["m00"])
        cY = int(moments["m01"] / moments["m00"])

        fixed_radius = 27.12  # pixels

        print(f"Centroid: ({cX}, {cY}), Fixed Radius: {fixed_radius:.2f} px")

        return (cX, cY), fixed_radius



# ---- App Entry Point ----

if __name__ == '__main__':
    root = tk.Tk()
    app = TestingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
