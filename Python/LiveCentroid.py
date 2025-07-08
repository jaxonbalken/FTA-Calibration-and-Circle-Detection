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

ports=serial.tools.list_ports.comports() #lists all available ports on the system 

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root #stores reference to tkinter root window, i should have made this shorter in hindsight
        self.root.title("Image Processor")

        self.x_coord = 0
        self.y_coord = 0
        self.coord_min = 0
        self.coord_max = 4095 #create max values for the corrdinates of the fiber tip, use later when making actuator function

        # Frame for holding the images
        self.image_frame = tk.Frame(root)
        self.image_frame.pack(fill=tk.BOTH, expand=True)

        # Frame for original image
        self.frame_original = tk.Frame(self.image_frame)
        self.frame_original.pack(side=tk.LEFT, padx=10, pady=10)

        # Frame for processed image
        self.frame_processed = tk.Frame(self.image_frame)
        self.frame_processed.pack(side=tk.LEFT, padx=10, pady=10)

        # Frame for XY controls 
        self.coord_frame = tk.Frame(self.image_frame)
        self.coord_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        # Element Number Controls
        # Define element number options
        self.element_options = [str(i) for i in range(1, 9)]  #options from 1 to 8
        self.selected_element = tk.StringVar(root)
        self.selected_element.set(self.element_options[0])  # Default value

        # Element Number Dropdown
        self.element_label = tk.Label(self.coord_frame, text="Element Number")
        self.element_label.pack()

        self.element_dropdown = tk.OptionMenu(self.coord_frame, self.selected_element, *self.element_options)
        self.element_dropdown.pack()

        #PREAMPS enable/disable button
        self.amps_var = tk.BooleanVar(value=False) #create boolean value to make sure the preamps always starts disabled

        #self.preamps = tk.Checkbutton(self.coord_frame, text = 'Enable XY Preamps', variable=self.amps_var, command=self.toggle_amp)
        #self.preamps.pack(padx=10,pady=10)

        #Buttons for x anf y coordinates
        # X Coordinate Controls
        self.xcoord_label = tk.Label(self.coord_frame, text="X Coordinate")
        self.xcoord_label.pack()

        self.xcoord_entry = tk.Entry(self.coord_frame) #create entry places for the xy coordinates
        self.xcoord_entry.pack()
        self.xcoord_entry.insert(0, "0")  # Set default value

        # Y Coordinate Controls
        self.ycoord_label = tk.Label(self.coord_frame, text="Y Coordinate")
        self.ycoord_label.pack()

        self.ycoord_entry = tk.Entry(self.coord_frame) #create entry places for the xy coordinates
        self.ycoord_entry.pack()
        self.ycoord_entry.insert(0, "0")  # Set default value

        # Coordinates Button
        #self.update_coords_button = tk.Button(self.coord_frame, text="Update Coordinates", command=self.update_coordinates)
        #self.update_coords_button.pack(pady=5)

        self.exposure_label = tk.Label(self.coord_frame, text="Exposure Time (μs):")
        self.exposure_label.pack()
        self.exposure_entry = tk.Entry(self.coord_frame)
        self.exposure_entry.pack()
        self.exposure_entry.insert(50000,'50000')

        self.gain_label = tk.Label(self.coord_frame, text="Gain Value:")
        self.gain_label.pack()
        self.gain_entry = tk.Entry(self.coord_frame)
        self.gain_entry.pack()
        self.gain_entry.insert(75,'75')
        
        # Buttons for load and process
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.load_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera) #button for caturing image 
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.load_button = tk.Button(self.button_frame, text="Capture Video", command=self.capture_video) #button for caturing image 
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        #self.process_button = tk.Button(self.button_frame, text="Process Image", command=self.process_image) #button for processing image 
        #self.process_button.pack(side=tk.LEFT, padx=5, pady=5)

        #self.automate_button = tk.Button(self.button_frame, text="Start Automation", command=self.test_run) # button for the automation process
        #self.automate_button.pack(side=tk.LEFT, padx=5, pady=5)

        #self.timelapse_button = tk.Button(self.button_frame, text="Time Lapse", command=self.time_lapse)
        #self.timelapse_button.pack(side=tk.LEFT, padx=5, pady=5)

        #self.clear_data_button = tk.Button(self.button_frame, text="Clear All Data", command=self.clear_all_data)
        #self.clear_data_button.pack(side=tk.RIGHT, padx=5, pady=5)

        #self.save_button = tk.Button(self.button_frame, text="Save Data", command=self.save_data) #button to save the automation process
        #self.save_button.pack(side=tk.RIGHT,padx= 10, pady=10)
        
        # Initialize images and circle centers
        self.original_image = None
        self.processed_image = None
        self.circle_centers = [] #create a dicitonary for the coordninates (in pixles) to be stored and plotted
        self.dac_values = [] #create a diciotnary for the DAC values so they can be compared to the change in xy
        self.movement_in_x = []
        self.movement_in_y = []
        self.microns_moved_in_x = []
        self.microns_moved_in_y = []
        self.microns_per_ADU_in_x = []
        self.microns_per_ADU_in_y = []
        self.circle_radii = []
        self.pixle_size = []
        self.data = [] # this dictionary is to append all of the data to so it can be saved to a csv file
        #self.circle_radius = []

# Initialize plot, label axis 
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Fiber Tip Centers")
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root) #creates widget that allows for matplotlib
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def connect_camera(self):
        # Initialize camera
        try: 
            env_filename = os.getenv('ZWO_ASI_LIB')
            asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll')
            self.num_cameras = asi.get_num_cameras()
            print(f"Number of cameras detected: {self.num_cameras}") #ask how many cameras are connected
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
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize camera: {str(e)}")
            print(f"Error initializing camera: {str(e)}")

    def display_image(self, frame):
            # Convert the frame (assuming it is a numpy array) to a PIL image
            pil_image = Image.fromarray(frame)

            # Convert the PIL image to ImageTk format so Tkinter can use it
            tk_image = ImageTk.PhotoImage(pil_image)

            # Update the Label widget with the new image
            #self.image_label.image = tk_image  # Keep a reference to avoid garbage collection


    def capture_video(self):
        if not self.camera_initialized:
                messagebox.showerror("Error", "Camera is not connected.")
                self.connect_camera()
                return
        
        gain_value = int(self.gain_entry.get())

        try: # Force any single exposure to be halted
                self.camera.stop_exposure()
        
        except (KeyboardInterrupt, SystemExit):
                raise
        except:
                pass
        
        print('Enabling video mode')
        self.camera.start_video_capture()

        try:
            while True:
                frame = self.camera.capture_video_frame()
                self.display_image(frame)
                self.root.update()
        except KeyboardInterrupt:
             print('mad messed up man')
             self.camera.stop_video_capture()

             

    # def display_image(self, image, frame):
    #     new_w = int(1936)
    #     new_h = int(1096)# Resizes image based on mulitplier 
    #     print(f'frame{frame}')
    #     resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    #     resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
    #     image_pil = Image.fromarray(resized_image)
    #     image_tk = ImageTk.PhotoImage(image_pil)
        
    #     # Create image on canvas
    #     if hasattr(frame, 'canvas'):
    #         frame.canvas.delete("all")
    #     else:
    #         frame.canvas = tk.Canvas(frame, width=new_w, height=new_h, bg='white')
    #         frame.canvas.pack()
    #     frame.canvas.create_image(0, 0, anchor=tk.NW, image=image_tk)
    #     frame.canvas.image = image_tk


# Make sure to include the rest of your class methods and initialization here

    def __del__(self):
        # Cleanup the camera on application close
        #if hasattr(self, 'ser'):
            #self.amp_off() # failsafe to make sure the preamp is always turned off when closing 
            #self.ser.close()
        if hasattr(self, 'camera'):
            self.camera.close()
            #asi.exit()
            self.root.destroy() # Closes the Tkinter window and exits the application


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop() #runs the app

