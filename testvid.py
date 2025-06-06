import os
import sys
import time
import csv
import traceback
import ctypes.wintypes

import tkinter as tk
from tkinter import messagebox  # Explicit imports, no wildcard
from tkinter import filedialog  # *** CHANGED/ADDED: import filedialog for save dialog ***

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

        self.current_roi = (887, 546, 640, 480)  # Default ROI

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
        self.target_label = tk.Label(master, text= 'Target Rate (fps)') 
        self.target_label.pack()
        self.target_entry = tk.Entry(master)
        self.target_entry.insert(100, '100')
        self.target_entry.pack()

        # Frame Rate Buttons
        self.framerate_button_frame = tk.Frame(master)
        self.framerate_button_frame.pack()
        preset_rates = [10, 30, 60, 100, 200]
        for rate in preset_rates:
            button = tk.Button(self.framerate_button_frame, text=f"{rate} fps", command=lambda r=rate: self.set_frame_rate(r))
            button.pack(side=tk.LEFT, padx=2, pady=2)

        #Number of frames input
        self.frames_label = tk.Label(master, text= 'Number Of Frames') 
        self.frames_label.pack()
        self.frames_entry = tk.Entry(master)
        self.frames_entry.insert(1000, '1000')
        self.frames_entry.pack()

        # ROI Selection Dropdown
        tk.Label(master, text="Select ROI Preset:").pack()
        self.roi_options = ["Full Frame", "640x480", "320x240"]
        self.selected_roi = tk.StringVar(master)
        self.selected_roi.set(self.roi_options[1])
        tk.OptionMenu(master, self.selected_roi, *self.roi_options, command=self.handle_roi_selection).pack()

        # ROI Position Control
        tk.Label(master, text="ROI Position (Start X, Start Y):").pack()
        self.roi_pos_frame = tk.Frame(master)
        self.roi_pos_frame.pack()
        self.roi_startx = tk.Entry(self.roi_pos_frame, width=5)
        self.roi_startx.insert(887, "887")
        self.roi_startx.pack(side=tk.LEFT)
        self.roi_starty = tk.Entry(self.roi_pos_frame, width=5)
        self.roi_starty.insert(546, "546")
        self.roi_starty.pack(side=tk.LEFT)
        tk.Button(master, text="Set ROI Position", command=self.set_roi_position).pack(pady=5)

        # Buttons
        self.sanity_check_button = tk.Button(master, text="Check Actual Frame Rate",command=self.run_sanity_check)
        self.sanity_check_button.pack(pady=5)
        self.button_frame = tk.Frame(master)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.cameraparameters_button = tk.Button(self.button_frame, text="Save Parameters", command = self.dummy_command)
        self.cameraparameters_button.pack(side=tk.TOP, padx=5, pady=5)

        # *** CHANGED/ADDED: Save last frames button ***
        self.save_button = tk.Button(self.button_frame, text="Save Last Frames", command=self.save_last_frames)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)
        # *** END CHANGE ***

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

    def save_parameters(self):
        try:
            self.saved_gain = int(self.gain_entry.get())
            self.saved_exposure = int(self.exposure_entry.get())
            self.saved_target_rate = int(self.target_entry.get())
            self.saved_num_frames = int(self.frames_entry.get())

            # Also save current ROI and position
            self.saved_roi = self.current_roi

            print("[PARAMETERS SAVED]")
            print(f"Gain: {self.saved_gain}")
            print(f"Exposure: {self.saved_exposure} µs")
            print(f"Target Rate: {self.saved_target_rate} fps")
            print(f"Number of Frames: {self.saved_num_frames}")
            print(f"ROI: {self.saved_roi}")

        except ValueError:
            messagebox.showerror("Save Failed", "Please enter valid numeric values.")
    
    def set_frame_rate(self, rate):
        self.target_entry.delete(0, tk.END)
        self.target_entry.insert(0, str(rate))

    def get_target_rate(self):
        try:
            return int(self.target_entry.get())
        except ValueError:
            print('Error!! Using Fallback,')
            return 100  # fallback/default
    def set_roi_position(self):
        try:
            x = int(self.roi_startx.get())
            y = int(self.roi_starty.get())
            # *** CHANGED/ADDED: subtract half width/height from x, y ***
            _, _, w, h = self.current_roi
            x -= w // 2
            y -= h // 2
            self.current_roi = (x, y, w, h)
            print(f"[ROI] Updated start position: ({x}, {y}), size ({w}x{h})")
        except ValueError:
            print("[ERROR] Invalid ROI position input.")

    def handle_roi_selection(self, selection):
        try:
            x = int(self.roi_startx.get())
            y = int(self.roi_starty.get())
            # *** CHANGED/ADDED: subtract half width/height for positioning ***
            if selection == "640x480":
                x -= 640 // 2
                y -= 480 // 2
            elif selection == "320x240":
                x -= 320 // 2
                y -= 240 // 2
        except ValueError:
            x, y = 887, 546

        if selection == "Full Frame":
            try:
                full_width, full_height, _, _ = self.camera.get_roi_format()
                self.current_roi = (0, 0, full_width, full_height)
                print(f"[ROI] Full Frame: {full_width}x{full_height}")
            except Exception:
                print("[ERROR] Full frame selection failed.")
        elif selection == "640x480":
            self.current_roi = (x, y, 640, 480)
            print(f"[ROI] Set to 640x480 at position ({x}, {y})")
        elif selection == "320x240":
            self.current_roi = (x, y, 320, 240)
            print(f"[ROI] Set to 320x240 at position ({x}, {y})")


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
            self.camera.set_image_type(asi.ASI_IMG_RAW8)
            self.camera.set_roi(width=320, height=240)  # Full frame
            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

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
        if self.streaming:
            try:
                frame = self.camera.capture_video_frame()
                if frame is not None:
                    self.display_frame(frame)
            except Exception as e:
                print(f"[ERROR] Update feed failed: {e}")

            self.master.after(30, self.update_feed)

    def display_frame(self, frame):
        # Convert the frame to an ImageTk format
        image = Image.fromarray(frame)
        image_tk = ImageTk.PhotoImage(image)
        self.video_frame.imgtk = image_tk
        self.video_frame.configure(image=image_tk)

    def run_sanity_check(self):
        if not self.camera_initialized:
            messagebox.showerror("Error", "Camera is not connected.")
            return
        try:
            frames = []
            num_frames = int(self.frames_entry.get())
            print(f"[INFO] Capturing {num_frames} frames for sanity check...")

            for i in range(num_frames):
                frame = self.camera.capture_video_frame()
                if frame is not None:
                    frames.append(frame)
                else:
                    print(f"[WARN] Frame {i} is None")
            self.last_captured_frames = frames  # *** CHANGED/ADDED: Save last frames for later use ***
            print(f"[INFO] Captured {len(frames)} frames.")

            # Show frame rate
            duration = num_frames / self.get_target_rate()
            actual_fps = len(frames) / duration
            print(f"[INFO] Actual FPS: {actual_fps:.2f}")

            # Save the last frames automatically? Or via button? Up to you.
        except Exception as e:
            print(f"[ERROR] Sanity check failed: {e}")

    # *** CHANGED/ADDED: Save last frames button callback ***
    def save_last_frames(self):
        if hasattr(self, 'last_captured_frames') and self.last_captured_frames:
            metadata = {
                "gain": self.gain_entry.get(),
                "exposure": self.exposure_entry.get(),
                "roi": str(self.current_roi),
                "target_fps": self.target_entry.get(),
                "frame_count": len(self.last_captured_frames),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_capture_data_to_h5(self.last_captured_frames, metadata)
        else:
            print("[INFO] No captured frames to save.")

    def save_capture_data_to_h5(self, frames, metadata):
        try:
            # *** CHANGED/ADDED: Use file dialog to get save location ***
            filename = filedialog.asksaveasfilename(
                title="Save capture data",
                defaultextension=".h5",
                filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")]
            )
            if not filename:
                print("[INFO] Save cancelled.")
                return

            with h5py.File(filename, 'w') as h5f:
                # Save metadata as attributes
                for key, value in metadata.items():
                    h5f.attrs[key] = value
                
                # Save frames as dataset
                h5f.create_dataset('frames', data=np.array(frames), compression="gzip")
            print(f"[INFO] Data saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Saving failed: {e}")


if __name__ == '__main__':
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
