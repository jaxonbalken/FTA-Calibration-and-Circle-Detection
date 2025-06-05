import os
import sys
import time
import csv
import traceback
import ctypes.wintypes

import tkinter as tk
from tkinter import messagebox  # Explicit imports, no wildcard

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



class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Live Video Feed")

        self.streaming = True
        self.update_feed()
        self.camera_initialized = False
        self.roi_info_logged = False
        self.camera = None
        self.streaming = False
        self.stream_start_time = None
        

        # Gain input
        self.gain_label = tk.Label(master, text="Gain:")
        self.gain_label.pack()
        self.gain_entry = tk.Entry(master)
        self.gain_entry.insert(0, "0")  # Default gain
        self.gain_entry.pack()

        # Exposure input
        self.exposure_label = tk.Label(master, text="Exposure (µs):")
        self.exposure_label.pack()
        self.exposure_entry = tk.Entry(master)
        self.exposure_entry.insert(30000, "30000")  # Default exposure
        self.exposure_entry.pack()

        #Target Rate input
        self.target_label = tk.Label(master, text= 'Target Rate') 
        self.target_label.pack()
        self.target_entry = tk.Entry(master)
        self.target_entry.insert(100, '100')
        self.target_entry.pack()

        #Number of frames input
        self.frames_label = tk.Label(master, text= 'Number Of Frames') 
        self.frames_label.pack()
        self.frames_entry = tk.Entry(master)
        self.frames_entry.insert(1000, '1000')
        self.frames_entry.pack()

        # Buttons

        self.button_frame = tk.Frame(master)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.cameraparameters_button = tk.Button(self.button_frame, text="Save Parameters", command = self.dummy_command)
        self.cameraparameters_button.pack(side=tk.TOP, padx=5, pady=5)
        
        # Video display
        self.video_frame = tk.Label(master)
        self.video_frame.pack()

        self.connect_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.start_button = tk.Button(self.button_frame, text="Start Feed", command=self.start_feed)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop Feed", command=self.stop_feed, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)


    def dummy_command(self):
        print('Button Pressed')

    def connect_camera(self):
        try:
            asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll')
            num_cameras = asi.get_num_cameras()
            if num_cameras == 0:
                messagebox.showerror("Error", "No cameras found.")
                self.master.destroy()
                return

            self.camera = asi.Camera(0)
            self.camera.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1)
            self.camera.set_roi()  # Full frame
            self.camera_initialized = True
            print("Camera Ready")  # Just print instead of showing a popup
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))

    def start_feed(self):
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
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

            self.camera.start_video_capture()
            self.streaming = True
            self.stop_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.DISABLED)
            self.update_feed()
        except Exception as e:
            messagebox.showerror("Capture Failed", str(e))

    def stop_feed(self):
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
            # Get ROI dimensions
            width, height, _, _ = self.camera.get_roi_format()
            if not self.roi_info_logged:
                print(f"[INFO] ROI Format: width={width}, height={height}")
                self.roi_info_logged = True

            # Prepare buffer
            expected_buffer_size = width * height  # Grayscale
            buffer = bytearray(expected_buffer_size)
            

            # corrected argument order: timeout first
            self.camera.get_video_data(1000, buffer)  # 1000 ms timeout

            actual_buffer_size = len(buffer)
            if actual_buffer_size != expected_buffer_size:
                raise ValueError(f"Unexpected buffer size. Expected {expected_buffer_size}, got {actual_buffer_size}")

            # Convert to numpy and reshape
            frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width))

            # Resize for display
            frame_resized = cv2.resize(frame, (640, 480))

            #reset roi to involve target


            # Convert to Tkinter-compatible image
            img = Image.fromarray(frame_resized, mode='L')
            imgtk = ImageTk.PhotoImage(image=img)

            # Update GUI frame
            self.video_frame.configure(image=imgtk)
            self.video_frame.image = imgtk  # prevent garbage collection

        except Exception as e:
            print("\n[ERROR] Live feed failed.")
            print(f"Message: {e}")
            traceback.print_exc()
            print("[INFO] Stopping video feed...\n")
            return
        self.master.after(30, self.update_feed)
    def on_close(self):
        if self.streaming:
            self.stop_feed()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

