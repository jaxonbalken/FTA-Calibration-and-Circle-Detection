import os
import sys
import time
import csv
import traceback
import ctypes.wintypes
from tkinter.filedialog import askopenfilename
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
        self.target_label = tk.Label(master, text= 'Playback Speed (fps)') 
        self.target_label.pack()
        self.target_entry = tk.Entry(master)
        self.target_entry.insert(30, '30')
        self.target_entry.pack()

        # Frame Rate Buttons
        self.framerate_button_frame = tk.Frame(master)
        self.framerate_button_frame.pack()
        preset_rates = [5,10, 30, 60, 100, 200]
        for rate in preset_rates:
            button = tk.Button(self.framerate_button_frame, text=f"{rate} fps", command=lambda r=rate: self.set_frame_rate(r))
            button.pack(side=tk.LEFT, padx=2, pady=2)

        #Number of frames input
        # self.frames_label = tk.Label(master, text= 'Number Of Frames') 
        # self.frames_label.pack()
        # self.frames_entry = tk.Entry(master)
        # self.frames_entry.insert(1000, '1000')
        # self.frames_entry.pack()

        # ROI Selection Dropdown
        tk.Label(master, text="Select ROI Preset:").pack()
        self.roi_options = ["Full Frame", "640x480", "320x240", "424x318"]
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

        self.play_button = tk.Button(self.button_frame, text="Play Saved Video", command=self.play_saved_video)
        self.play_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.analyze_button = tk.Button(self.button_frame, text="Analyze Centroids", command=self.analyze_saved_centroids)
        self.analyze_button.pack(side=tk.LEFT, padx=5, pady=5)

        tk.Button(master, text="Find Centroid", command=self.find_centroid_in_current_frame).pack(pady=5)



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
            self.capture_duration = duration
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
            self.master.after(1, self.update_feed)

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
            num_frames = 1000
            
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
            print(f'[INFO] Using {num_frames} frames')
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
            if hasattr(self, 'capture_duration') and self.capture_duration > 0:
                actual_fps = len(self.live_captured_frames) / self.capture_duration
            else:
                actual_fps = "unknown"

            metadata = {
                "gain": self.gain_entry.get(),
                "exposure": self.exposure_entry.get(),
                "roi": str(self.current_roi),
                "actual_fps": str(actual_fps),
                "frame_count": len(self.live_captured_frames),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            filename = self.save_capture_data_to_h5(self.live_captured_frames, metadata)

            if filename:
                print("\n[VIDEO SAVED]")
                print(f"File: {filename}")
                print(f"Timestamp: {metadata['timestamp']}")
                print(f"Gain: {metadata['gain']}")
                print(f"Exposure: {metadata['exposure']} µs")
                print(f"ROI: {metadata['roi']}")
                print(f"Frame Count: {metadata['frame_count']}")
                print(f"Actual FPS: {metadata['actual_fps']}")
                print()
        else:
            print("[INFO] No frames captured. Nothing to save.")


    def save_capture_data_to_h5(self, frames, metadata):
        try:
            filename = filedialog.asksaveasfilename(
                title="Save capture data",
                defaultextension=".h5",
                filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")]
            )
            if not filename:
                print("[INFO] Save cancelled.")
                return None

            with h5py.File(filename, 'w') as h5f:
                for key, value in metadata.items():
                    h5f.attrs[key] = value
                h5f.create_dataset('frames', data=np.array(frames), compression="gzip")
            print(f"[INFO] Data saved to {filename}")
            return filename
        except Exception as e:
            print(f"[ERROR] Saving failed: {e}")
            return None

    def play_saved_video(self):
        from tkinter.filedialog import askopenfilename

        file_path = askopenfilename(
            title="Select HDF5 File",
            filetypes=[("HDF5 files", "*.h5 *.hdf5"), ("All files", "*.*")]
        )

        if not file_path:
            print("[INFO] Playback cancelled.")
            return

        if not os.path.exists(file_path):
            messagebox.showerror("File Error", f"File not found: {file_path}")
            return

        try:
            with h5py.File(file_path, 'r') as f:
                if 'frames' not in f:
                    messagebox.showerror("Data Error", "'frames' dataset not found.")
                    return
                frames = f['frames'][:]
                # Try reading the stored capture FPS
                capture_fps = float(f.attrs.get('actual_fps', 120))  # fallback default if not stored

            frame_count = len(frames)

            # === Get current GUI playback rate ===
            try:
                playback_fps = int(self.target_entry.get())
            except ValueError:
                playback_fps = 30  # fallback

            slowdown_factor = capture_fps / playback_fps
            delay = int(1000 / playback_fps)
            original_duration = frame_count / capture_fps
            expected_playback_duration = frame_count / playback_fps

            print(f"\n[PLAYBACK INFO]")
            print(f"File: {os.path.basename(file_path)}")
            print(f"Frames: {frame_count}")
            print(f"Original FPS (from file): {capture_fps:.2f}")
            print(f"Playback FPS (from GUI): {playback_fps}")
            print(f"Slowdown Factor: {slowdown_factor:.2f}x")
            print(f"Original Duration: {original_duration:.2f} sec")
            print(f"Expected Playback Duration: {expected_playback_duration:.2f} sec")
            print("Press 'q' to quit playback early.\n")

            start_time = time.time()

            for i, frame in enumerate(frames):
                cv2.imshow("Slow Motion Playback - Press 'q' to Quit", frame)
                key = cv2.waitKey(delay)
                if key == ord('q') or key == 27:
                    print("[INFO] Playback stopped by user.")
                    break

            end_time = time.time()
            actual_duration = end_time - start_time
            actual_fps = frame_count / actual_duration if actual_duration > 0 else 0

            cv2.destroyAllWindows()

            print(f"\n[INFO] Playback finished.")
            print(f"[INFO] Actual Playback Time: {actual_duration:.2f} sec")
            print(f"[INFO] Actual FPS: {actual_fps:.2f}")
            print(f"[INFO] Actual Slowdown Factor: {capture_fps / actual_fps:.2f}x")

        except Exception as e:
            messagebox.showerror("Playback Error", str(e))
            print(f"[ERROR] Playback failed: {e}")
    
    


    def analyze_saved_centroids(self):
        file_path = filedialog.askopenfilename(
            title="Select HDF5 File for Centroid Analysis",
            filetypes=[("HDF5 files", "*.h5 *.hdf5"), ("All files", "*.*")]
        )

        if not file_path or not os.path.exists(file_path):
            print("[INFO] No file selected or file not found.")
            return

        try:
            with h5py.File(file_path, 'r') as f:
                if 'frames' not in f:
                    messagebox.showerror("Error", "No 'frames' dataset found in the file.")
                    return

                frames = f['frames'][:]
                print(f"\n[INFO] Loaded {len(frames)} frames from {file_path}")

                centroids = []
                movements = []
                last_centroid = None

                total_start = time.time()

                for i, frame in enumerate(frames):
                    frame_start = time.time()
                    print(f"\n--- Frame {i+1} ---")

                    # Apply thresholding
                    ret, thresh = cv2.threshold(frame, 127, 255, 0)
                    M = cv2.moments(thresh)

                    # Convert to BGR for display
                    debug_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        centroids.append((cX, cY))
                        print(f"[Centroid] (X: {cX}, Y: {cY})")

                        if last_centroid:
                            dx = cX - last_centroid[0]
                            dy = cY - last_centroid[1]
                            dist = np.sqrt(dx**2 + dy**2)
                            print(f"[Motion] ΔX: {dx}, ΔY: {dy}, Distance: {dist:.2f} pixels")
                            movements.append(dist)
                        else:
                            print("[Motion] First valid centroid, no motion calculated.")
                            movements.append(0)

                        last_centroid = (cX, cY)

                        # Draw the centroid
                        cv2.circle(debug_frame, (cX, cY), 4, (0, 0, 255), -1)
                    else:
                        centroids.append((None, None))
                        movements.append(0)
                        print("[Centroid] Not detected — empty or invalid frame.")

                    # Add frame number for context
                    cv2.putText(debug_frame, f"Frame: {i+1}", (10, 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

                    # Show live debug window
                    cv2.imshow("Centroid Debug Preview", debug_frame)
                    key = cv2.waitKey(1)
                    if key == 27:  # Esc key to exit preview early
                        print("[INFO] Debug preview interrupted by user.")
                        break

                    frame_end = time.time()
                    print(f"[Timing] Frame processing time: {frame_end - frame_start:.4f} sec")

                cv2.destroyAllWindows()

                # Summary
                total_end = time.time()
                total_time = total_end - total_start
                avg_movement = np.mean([m for m in movements if m is not None])
                max_movement = np.max([m for m in movements if m is not None])

                print(f"\n========== SUMMARY ==========")
                print(f"Total Frames: {len(frames)}")
                print(f"Frames with Valid Centroid: {len([c for c in centroids if c != (None, None)])}")
                print(f"Average Movement: {avg_movement:.2f} pixels")
                print(f"Max Movement: {max_movement:.2f} pixels")
                print(f"Total Processing Time: {total_time:.2f} seconds")
                print(f"Average Per Frame: {total_time / len(frames):.4f} seconds")
                print(f"==============================\n")

                # Save CSV
                save_prompt = input("Do you want to save the centroid data to a CSV file? (y/n): ").strip().lower()
                if save_prompt == 'y':
                    csv_path = file_path.replace('.h5', '_centroids.csv')
                    with open(csv_path, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['Frame', 'Centroid_X', 'Centroid_Y', 'Movement (pixels)'])
                        for i, (centroid, move) in enumerate(zip(centroids, movements)):
                            x, y = centroid if centroid != (None, None) else ('None', 'None')
                            writer.writerow([i, x, y, move])
                    print(f"[INFO] CSV saved to:\n{csv_path}")
                else:
                    print("[INFO] CSV not saved.")

        except Exception as e:
            print(f"[ERROR] Centroid analysis failed: {e}")
            traceback.print_exc()



    def find_centroid_in_current_frame(self):
        if not hasattr(self, 'live_captured_frames') or not self.live_captured_frames:
            messagebox.showwarning("No Frame", "No frames captured yet.")
            return

        frame = self.live_captured_frames[-1].copy()
        try:
            start_time = time.time()

            # Threshold to binary
            ret, thresh = cv2.threshold(frame, 127, 255, 0)

            # Compute moments
            M = cv2.moments(thresh)

            if M["m00"] == 0:
                messagebox.showerror("Centroid Error", "Unable to compute centroid (m00 is zero).")
                return

            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])

            # Print for debug
            print(f"[CENTROID] Found at: ({cX}, {cY})")

            # Update UI fields
            self.roi_startx.delete(0, tk.END)
            self.roi_startx.insert(0, str(cX))

            self.roi_starty.delete(0, tk.END)
            self.roi_starty.insert(0, str(cY))

            # Visualize result in OpenCV
            annotated = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            cv2.circle(annotated, (cX, cY), 10, (0, 0, 255), 2)
            cv2.putText(annotated, f"Centroid: ({cX}, {cY})", (cX + 15, cY + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imshow("Detected Centroid", annotated)
            cv2.waitKey(500)
            cv2.destroyAllWindows()

            duration = time.time() - start_time
            print(f"[INFO] Centroid detection took {duration:.3f} seconds.")

        except Exception as e:
            print(f"[ERROR] Failed to find centroid: {e}")
            traceback.print_exc()



if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

