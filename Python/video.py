import os
import sys
import time
import csv
import traceback
import ctypes.wintypes

import tkinter as tk
from tkinter import messagebox 
from tkinter import filedialog # Explicit imports, no wildcard

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

        #self.current_roi = (887, 546, 640, 480)  # Default ROI

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
        self.roi_startx.insert(968, "968")
        self.roi_startx.pack(side=tk.LEFT)
        self.roi_starty = tk.Entry(self.roi_pos_frame, width=5)
        self.roi_starty.insert(548, "548")
        self.roi_starty.pack(side=tk.LEFT)
        tk.Button(master, text="Set ROI Position", command=self.set_roi_position).pack(pady=5)


        # Buttons
        self.sanity_check_button = tk.Button(master, text="Check Actual Frame Rate", command=self.run_sanity_check)
        self.sanity_check_button.pack(pady=5)

        self.button_frame = tk.Frame(master)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # self.cameraparameters_button = tk.Button(self.button_frame, text="Save Parameters", command=self.dummy_command)
        # self.cameraparameters_button.pack(side=tk.TOP, padx=5, pady=5)

        self.save_button = tk.Button(self.button_frame, text="Save Last Frames", command=self.save_last_frames)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.connect_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.start_button = tk.Button(self.button_frame, text="Start Feed", command=self.start_feed)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop Feed", command=self.stop_feed, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.video_frame = tk.Label(master)
        self.video_frame.pack()

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
            _, _, w, h = self.current_roi
            self.current_roi = (x, y, w, h)
            print(f"[ROI] Updated start position: ({x}, {y}), size ({w}x{h})")
        except ValueError:
            print("[ERROR] Invalid ROI position input.")
    
    def update_current_roi_from_ui(self):
        """Update self.current_roi based on dropdown and ROI position input."""
        try:
            center_x = int(self.roi_startx.get())
            center_y = int(self.roi_starty.get())
            roi_str = self.selected_roi.get()
            print(f"[DEBUG] ROI selection: {roi_str}, Tareget Center Coord: ({center_x}, {center_y})")
            if roi_str == "Full Frame":
                # Full Frame will be set explicitly elsewhere using the camera info
                full_width, full_height, _, _ = self.camera.get_roi_format()
                self.current_roi = (0, 0, full_width, full_height)
                print(f"[ROI] Full Frame: {full_width}x{full_height}")
            else:
                w, h = map(int, roi_str.split('x'))

                start_x = center_x - w // 2
                start_y = center_y - h // 2

                self.current_roi = (start_x, start_y, w, h)
                print(f"[DEBUG] Adjusted Target ROI: Start({start_x}, {start_y}), Size({w}x{h})")
        except Exception as e:
            print(f"[ERROR] Failed to update ROI from UI: {e}")
            messagebox.showerror("Invalid ROI", "ROI values must be numeric and in WIDTHxHEIGHT format.")

    def handle_roi_selection(self, selection):
        if selection == "Full Frame":
            try:
                self.camera.set_roi(width=1936, height=1096) 
                print(f"[ROI] Full Frame: {1936}x{1096}")
            except Exception:
                print("[ERROR] Full frame selection failed.")
        else:
            print(f"[DEBUG] ROI dropdown changed to: {selection}")
            self.update_current_roi_from_ui()


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
            self.camera.set_roi(width=320, height=240) 
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
            print(f"[DEBUG] Gain: {gain_value}, Exposure: {exposure_time} µs")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for gain and exposure.")
            return

        try:
            self.update_current_roi_from_ui()
            x, y, w, h = self.current_roi
            self.camera.set_roi(start_x=x, start_y=y, width=w, height=h)
            print(f"[DEBUG] Applying ROI before video capture: Start({x}, {y}), Size({w}x{h})")
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

            self.camera.start_video_capture()
            self.streaming = True
            self.live_captured_frames = []  # Start a new buffer
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
            frame_start_time = time.time()
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
                    # Save to live frame buffer
            if not hasattr(self, 'live_captured_frames'):
                self.live_captured_frames = []
            self.live_captured_frames.append(frame.copy())  # Save original (not resized) frame
            if len(self.live_captured_frames) > 5000:
                self.live_captured_frames.pop(0)


            # Convert to Tkinter-compatible image
            img = Image.fromarray(frame_resized, mode='L')
            imgtk = ImageTk.PhotoImage(image=img)

            # Update GUI frame
            self.video_frame.configure(image=imgtk)
            self.video_frame.image = imgtk  # prevent garbage collection
            rate = self.get_target_rate()
            frame_interval_us = 1e6 / rate
            elapsed_us = (time.time() - frame_start_time) * 1e6
            delay_ms = max(1, int((frame_interval_us - elapsed_us) / 1000))
            self.master.after(delay_ms, self.update_feed)

        except Exception as e:
            print("\n[ERROR] Live feed failed.")
            print(f"Message: {e}")
            traceback.print_exc()
            print("[INFO] Stopping video feed...\n")
            return
       #self.master.after(30, self.update_feed)
        
    def on_close(self):
        if self.streaming:
            self.stop_feed()
        self.master.destroy()

    def run_sanity_check(self):
        try:
            num_frames = int(self.frames_entry.get())
            
        except ValueError:
            num_frames = 100
        self.check_actual_frame_rate(num_frames=num_frames)

    def check_actual_frame_rate(self, num_frames=100):
        if not self.camera_initialized:
            print("[ERROR] Camera not initialized.")
            return

        rate_frame = int(self.target_entry.get())
        
        print(f"[INFO] Starting sanity check: capturing {num_frames} frames...")
        print(f"[INFO] Gain: {self.gain_entry.get()}")
        print(f'[INFO] Exposure: {self.exposure_entry.get()} microseconds')
        print(f'[INFO] Target frame rate: {rate_frame} fps')

        try:
            # === Match current ROI format ===
            self.update_current_roi_from_ui()
            x, y, w, h = self.current_roi
            self.camera.set_roi(start_x=x, start_y=y, width=w, height=h)
            print(f"[INFO] Using ROI for sanity check: Start({x},{y}), Size({w}x{h})")
            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
            self.camera.set_control_value(asi.ASI_GAIN, gain_value)
            self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)


            self.camera.start_video_capture()

            frames = []
            t_start = time.time()

            for _ in range(num_frames):
                frame = self.camera.capture_video_frame(timeout=1000)
                frames.append(frame)

            t_end = time.time()
            self.camera.stop_video_capture()

            actual_rate = num_frames / (t_end - t_start)
            print(f"[RESULT] Actual capture rate: {actual_rate:.2f} fps")

        except Exception as e:
            print("[ERROR] Sanity check failed:", e)
            traceback.print_exc()

    def save_last_frames(self):
        self.stop_feed()
        if hasattr(self, 'live_captured_frames') and self.live_captured_frames:
            metadata = {
                "gain": self.gain_entry.get(),
                "exposure": self.exposure_entry.get(),
                "roi": str(self.current_roi),
                "target_fps": self.target_entry.get(),
                "frame_count": len(self.live_captured_frames),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_capture_data_to_h5(self.live_captured_frames, metadata)
        else:
            messagebox.showinfo("No Frames", "No frames have been captured during live feed.")

    def save_capture_data_to_h5(self, frames, metadata):
        try:
            filename = filedialog.asksaveasfilename(
                title="Save capture data",
                defaultextension=".h5",
                filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")]
            )
            if not filename:
                print("[INFO] Save cancelled.")
                return

            with h5py.File(filename, 'w') as h5f:
                for key, value in metadata.items():
                    h5f.attrs[key] = value
                h5f.create_dataset('frames', data=np.array(frames), compression="gzip")
            print(f"[INFO] Data saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Saving failed: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

