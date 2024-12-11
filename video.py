import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import zwoasi as asi
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from time import time
import pycromanager
import sys
from scipy import optimize
from time import sleep
import serial
import serial.tools.list_ports
import csv
from datetime import date


class CameraApp:
    
    def __init__(self, master):
        self.master = master
        self.master.title("Live Video Feed")
        
        # Initialize camera
        self.camera_initialized = False
        self.camera = None  # Your camera initialization logic here
        
        # Create UI elements
        self.gain_label = tk.Label(master, text="Gain:")
        self.gain_label.pack()
        self.gain_entry = tk.Entry(master)
        self.gain_entry.pack()

        self.exposure_label = tk.Label(master, text="Exposure (µs):")
        self.exposure_label.pack()
        self.exposure_entry = tk.Entry(master)
        self.exposure_entry.pack()

        self.start_button = tk.Button(master, text="Start Feed", command=self.start_feed)
        self.start_button.pack()
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.load_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera) #button for caturing image 
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)


        self.video_frame = tk.Label(master)
        self.video_frame.pack()

        self.camera_initialized = self.connect_camera()

  
    def connect_camera(self):
        # Initialize camera
        env_filename = os.getenv('ZWO_ASI_LIB')
        asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll')
        self.num_cameras = asi.get_num_cameras() #ask how many cameras are connected
        print('Camera connected')
        if self.num_cameras == 0: #if no cameras are connected, return this message 
            messagebox.showerror("Error", "No cameras found")
            self.root.destroy() # Closes the Tkinter window and exits the application
            return
        
        self.camera = asi.Camera(0) #initializes the camera and saves it to this variable, first camera selected 
        self.camera.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1) #sets the contol value to enable high speed mode, 1 enables the mode
        self.camera.set_roi() #sets range of intrest, roi is set for the entire image 
        self.camera_initialized = True  # Set camera initialization flag
        print('Camera Ready')

    def start_feed(self):
        
        if not self.camera_initialized:
            messagebox.showerror("Error", "Camera is not connected.")
            self.connect_camera()
            return
        self.num_cameras = asi.get_num_cameras() #ask how many cameras are connected
        print('Camera connected')
        if self.num_cameras == 0: #if no cameras are connected, return this message 
            messagebox.showerror("Error", "No cameras found")
            self.root.destroy() # Closes the Tkinter window and exits the application
            return

        # Get gain and exposure values
        try:
            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for gain and exposure.")
            return

        # Set camera gain and exposure
        self.camera.set_control_value(asi.ASI_GAIN, gain_value)
        self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

        self.update_feed()

    def update_feed(self):
        try:
            # Capture image from the camera
            frame = self.camera.capture()
            self.display_image(frame)
        except Exception as e:
            print(f"Error capturing image: {e}")
            messagebox.showerror("Error", "Failed to capture image from camera.")

        # Call this method again after 33 ms (approximately 30 fps)
        self.master.after(33, self.update_feed)

    def display_image(self, frame):
        # Convert the image to a format Tkinter can use
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (640, 480))  # Resize as needed
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2Tkinter)
        
        # Create a PhotoImage and display it
        self.photo = tk.PhotoImage(image=img)
        self.video_frame.configure(image=self.photo)
        self.video_frame.image = self.photo  # Keep a reference to avoid garbage collection

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
