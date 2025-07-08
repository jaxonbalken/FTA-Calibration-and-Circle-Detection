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

# env_filename=os.getenv('ZWO_ASI_LIB') #initialize camera and find its directory where it is located 
# asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll') #directory of camera 

ports=serial.tools.list_ports.comports() #lists all available ports on the system 

#application that can connect the camera, connect the XY Preamps, controlls the xy position of the fiber tip, 
#takes a photo of the fiber tip, processes the image, and plots the center of the fiber tip
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

        self.exposure_label = tk.Label(self.coord_frame, text="Exposure Time (μs):")
        self.exposure_label.pack()
        self.exposure_entry = tk.Entry(self.coord_frame)
        self.exposure_entry.pack()
        self.exposure_entry.insert(94000,'94000')

        self.gain_label = tk.Label(self.coord_frame, text="Gain Value:")
        self.gain_label.pack()
        self.gain_entry = tk.Entry(self.coord_frame)
        self.gain_entry.pack()
        self.gain_entry.insert(0,'0')

        self.Xcoord_label = tk.Label(self.coord_frame, text= 'X Coord Circle')
        self.Xcoord_label.pack()
        self.Xcoord_entry = tk.Entry(self.coord_frame)
        self.Xcoord_entry.pack()
        self.Xcoord_entry.insert(846, '846')

        self.Ycoord_label = tk.Label(self.coord_frame, text= 'Y Coord Circle')
        self.Ycoord_label.pack()
        self.Ycoord_entry = tk.Entry(self.coord_frame)
        self.Ycoord_entry.pack()
        self.Ycoord_entry.insert(560, '560')

        self.rad_label = tk.Label(self.coord_frame, text= 'Radius')
        self.rad_label.pack()
        self.rad_entry = tk.Entry(self.coord_frame)
        self.rad_entry.pack()
        self.rad_entry.insert(170,'170')

        
        # Buttons for load and process
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.load_button = tk.Button(self.button_frame, text="Connect Camera", command=self.connect_camera) #button for caturing image 
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.load_button = tk.Button(self.button_frame, text="Capture Image", command=self.capture_image_from_camera) #button for caturing image 
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.process_button = tk.Button(self.button_frame, text="Process Image", command=self.process_image) #button for processing image 
        self.process_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.timelapse_button = tk.Button(self.button_frame, text="Time Lapse", command=self.time_lapse)
        self.timelapse_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_data_button = tk.Button(self.button_frame, text="Clear All Data", command=self.clear_all_data)
        self.clear_data_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.save_button = tk.Button(self.button_frame, text="Save Data", command=self.save_data) #button to save the automation process
        self.save_button.pack(side=tk.RIGHT,padx= 10, pady=10)
        
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
        self.info_frame = tk.Frame(root)
        self.info_frame.pack()

        self.awayx_label = tk.Label(self.info_frame, text= 'X mm Away', font=("Arial", 18))
        self.awayx_label.pack()

        self.awayy_label = tk.Label(self.info_frame, text= 'Y mm Away', font=("Helvetica", 18))
        self.awayy_label.pack()

        self.totaldistance_label = tk.Label(self.info_frame, text= 'Total Distance mm', font=("Helvetica", 18))
        self.totaldistance_label.pack()

        # self.fig, self.ax = plt.subplots()
        # self.ax.set_title("Fiber Tip Centers")
        # self.ax.set_xlabel("X")
        # self.ax.set_ylabel("Y")
        # self.canvas = FigureCanvasTkAgg(self.fig, master=self.root) #creates widget that allows for matplotlib
        # self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

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


    def update_coordinates(self): #reads the x and y values from the input and passes it throught the set_DAC function
        try:
            x = int(self.xcoord_entry.get()) #gets user input, which is from the text from the xy coordinate entry button, converts to integer so nothing gets messed up 
            y = int(self.ycoord_entry.get())
              # Get the element number from dropdown

            if self.coord_min <= x <= self.coord_max and self.coord_min <= y <= self.coord_max:
                print(f"Setting DAC to X: {x}, Y: {y}") # make sure the values are in the accepted range
                self.set_DAC(x,y) #if they are, call the DAC function to set the new coordinates 

            else:
                messagebox.showerror("Error", f"Coordinates must be between {self.coord_min} and {self.coord_max}.") #return error if integer is too big or too small 
        except ValueError: #return error if xy values cannot be converted to integers 
            messagebox.showerror("Error", "Invalid input! Please enter numeric values.")

    def toggle_amp(self, *args): # toggle function for the enable/disable preamps button. *args accepts any number of arguements 
        if self.amps_var.get(): #retrieves the current value of self.amps_var, since the boolean is originally false, it should start out disabled
            self.amp_on() #if returns true, preamp will be enabled 
        else:
            self.amp_off() #if returns false, preamp will be disabled
        return
    
    def dummy_command(self): # Placeholder for future functionality, debug
        print("Button clicked")
        output = self.original_image.copy()
        circle_center_x = int(self.Xcoord_entry.get())
        circle_center_y = int(self.Ycoord_entry.get())
        radius_circle = int(self.rad_entry.get())

        cv2.circle(output, (circle_center_x,circle_center_y), radius_circle, (255,0,0), 2)
        color_mapped_image = cv2.applyColorMap(output, cv2.COLORMAP_PLASMA) # changes the output photo to plasma color map(looks cool)
        self.processed_image = color_mapped_image #assign value to new image so it can be displayed. idk why i did this i realize now that this is not needed 
        self.display_image(self.processed_image, self.frame_processed)
        self.update_plot(mmdistance_x, mmdistance_y, mmdistance)  # Update the existing plot with new data
        print(f'x center : {circle_center_x}')
        print(f'y center : {circle_center_y}')

    def time_lapse(self, rounds=10):
        for i in range(rounds):
            sleep(10)
            print(f"Starting Time Lapse, Round {i+1} of {rounds} Rounds")
            self.capture_image_from_camera()
            print('Processing Image')
            sleep(2)
            self.process_image()
            print('Image processed, waiting for next round')
            sleep(5)
        print("DONE")
    
    def test_run(self): 
        sleep(10) #this is a function to go through some of the DAC values. I use this so i can look at the fiber
        self.capture_image_from_camera()
        

    def capture_image_from_camera(self, max_retries=3, retry_delay=1):
        """Capture an image from the camera with retry mechanism if the first attempt fails."""
        if not self.camera_initialized:
            messagebox.showerror("Error", "Camera is not connected.")
            self.connect_camera()
            return

        # Attempt to read gain and exposure values
        try:
            gain_value = int(self.gain_entry.get())
            exposure_time = int(self.exposure_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for gain and exposure.")
            return

        attempt = 0
        while attempt < max_retries:
            try:
                # Print status and attempt capture
                print(f'Attempt {attempt + 1} of {max_retries} to capture image.')

                # Set exposure time (in microseconds)
                self.camera.set_control_value(asi.ASI_EXPOSURE, exposure_time)

                # Set gain value
                self.camera.set_control_value(asi.ASI_GAIN, gain_value)

                print('Capturing Image...')
                sleep(1)

                # Capture image
                original_image = self.camera.capture()
                self.original_image = original_image
                self.display_image(original_image, self.frame_original)
                print("Image captured successfully.")
                return  # Exit if image capture was successful

            except Exception as e:
                # Handle exceptions and retry
                print(f"Error capturing image: {e}")
                attempt += 1
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                else:
                    messagebox.showerror("Error", "Failed to capture image from camera after multiple attempts.")

    def process_image(self):
            if self.original_image is None:
                messagebox.showerror("Error", "No image captured")
                return
            
            global mmdistance_x, mmdistance_y, mmdistance
        
            output = self.original_image.copy()

            # convert the grayscale image to binary image
            ret,thresh = cv2.threshold(self.original_image,127,255,0)
            
            # calculate moments of binary image
            M = cv2.moments(thresh)

            # calculate x,y coordinate of center
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # put text and highlight the center
            cv2.circle(output, (cX, cY), 5, (0, 255, 255), -1)
            cv2.putText(output, "centroid", (cX - 25, cY - 25),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            #
            #  display the image
            #cv2.imshow("Image", output)
            circle_center_x = int(self.Xcoord_entry.get())
            circle_center_y = int(self.Ycoord_entry.get())
            radius_circle = int(self.rad_entry.get()) #pixels
            
            #cv2.circle(output, (circle_center_x,circle_center_y), radius_circle, (255,0,0), 2)
            #cv2.circle(output, (circle_center_x, circle_center_y), 5, (0, 255, 0), -1)
            
            distance_x = cX-circle_center_x
            distance_y = cY-circle_center_y
            distance = np.sqrt((distance_x) ** 2 + (distance_y)**2)
            print(f'X distance between ferrule and lense center: {distance_x*1} pixels')
            print(f'Y distance between ferrule and lense center: {distance_y*-1} pixels')
            print(f'distance between ferrule and lense center: {distance} pixels')

            # print(cX)
            # print(cY)
            self.circle_centers.append((cX, cY))
            circle_radius = 37
            # Crop the output back to the original image size
            # Add to data storage with element number
            
            inside_diameter = 97.5 #mm
            inside_radius = inside_diameter / 2


            cv2.waitKey(0)
            #print(f'Element #{element}')
            print(f"Recorded circle centers: {self.circle_centers}")

            fiber_size = 125
            #pixel_size = fiber_size / (circle_radius * 2)
            pixel_size = inside_radius / radius_circle
            #print("Detected circle radii:", circle_radius, 'Pixels')
            #print("Detected pixel size", pixel_size, 'mm/pixel')

            mmdistance_x = distance_x*pixel_size
            mmdistance_y = distance_y*pixel_size*-1
            mmdistance = distance*pixel_size
            print(f'X distance between ferrule and lense center: {mmdistance_x} mm')
            print(f'Y distance between ferrule and lense center: {mmdistance_y} mm')
            print(f'distance between ferrule and lense center: {mmdistance} mm')
            print(f'Pixel Size: {pixel_size}')

            self.circle_radii.append(circle_radius)
            self.pixle_size.append(pixel_size)

            color_mapped_image = cv2.applyColorMap(output, cv2.COLORMAP_PLASMA) # changes the output photo to plasma color map(looks cool)
            self.processed_image = color_mapped_image #assign value to new image so it can be displayed. idk why i did this i realize now that this is not needed 
            self.display_image(self.processed_image, self.frame_processed)
            self.update_plot(mmdistance_x, mmdistance_y, mmdistance)  # Update the existing plot with new data
            
            if len(self.circle_centers) > 1:
                previous_center = self.circle_centers[-2] # second most recent input in the list 
                current_center = self.circle_centers[-1] #most recent input in the list 
                
                movement_x = abs(current_center[0] - previous_center[0]) # movement will be the current center minus the previous ceneter 
                movement_y = abs(current_center[1] - previous_center[1]) # same but take the second value of the 2d matrix

                microns_movedx = movement_x * pixel_size # use calculated pixel size to find the amount of microns moved in the x and y dir
                microns_movedy = movement_y * pixel_size

                self.movement_in_x.append(movement_x) #save values of x and y that the fiber has moved (pixels) 
                self.movement_in_y.append(movement_y)

                self.microns_moved_in_x.append(microns_movedx) # save values for the amount of microns moved, using the conversion between microns and pixels
                self.microns_moved_in_y.append(microns_movedy)
                print(f"Movement -- X: {movement_x} pixels, Y: {movement_y} pixels")
                print(f'Microns Moved X: {self.microns_moved_in_x}')
                print(f'Microns Moved Y: {self.microns_moved_in_y}')

            if len(self.dac_values) > 1: # this is to use the saved values from the circle centers and the xy coords
                
                previous_DAC = self.dac_values[-2] # use the second to last input to find the previous dac count 
                current_DAC = self.dac_values[-1] # use the last input to find the current dac count
                delta_DACx = abs(current_DAC[0]-previous_DAC[0]) # subtract these for both the x and y to find the change in dac
                delta_DACy = abs(current_DAC[1]-previous_DAC[1])
                
                print(f'Dac values{self.dac_values}')
                print(f'Change in DAC {delta_DACx} in X and {delta_DACy} in Y')
    
                if delta_DACx != 0:
                    microns_per_ADUx = microns_movedx / delta_DACx
                else:
                    microns_per_ADUx = 0

                if delta_DACy != 0:
                    microns_per_ADUy = microns_movedy / delta_DACy
                else:
                    microns_per_ADUy = 0

                self.microns_per_ADU_in_x.append(microns_per_ADUx)
                self.microns_per_ADU_in_y.append(microns_per_ADUy)
                print(f'Microns/ADU X: {self.microns_per_ADU_in_x}')
                print(f'Microns/ADU Y: {self.microns_per_ADU_in_y}')
            
    def clear_all_data(self):
    # Reset all lists and variables
        self.original_image = None
        self.processed_image = None
        self.circle_centers = []
        self.dac_values = []
        self.movement_in_x = []
        self.movement_in_y = []
        self.microns_moved_in_x = []
        self.microns_moved_in_y = []
        self.microns_per_ADU_in_x = []
        self.microns_per_ADU_in_y = []
        self.DACx = []
        self.data = []
        self.circle_radii = []
        self.pixle_size = []
        
        # Optionally clear the plots
        self.ax.clear()
        self.ax.set_title("Fiber Tip Centers")
        self.ax.set_xlabel("X Pixels")
        self.ax.set_ylabel("Y Pixels")
        self.canvas.draw()


        print("All data cleared.")

    def display_image(self, image, frame):
        scale = 0.5 #allows you to change the size of the image in the tkinter window 
        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)# Resizes image based on mulitplier 
        
        resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(resized_image)
        image_tk = ImageTk.PhotoImage(image_pil)
        
        # Create image on canvas
        if hasattr(frame, 'canvas'):
            frame.canvas.delete("all")
        else:
            frame.canvas = tk.Canvas(frame, width=new_w, height=new_h, bg='white')
            frame.canvas.pack()
        frame.canvas.create_image(0, 0, anchor=tk.NW, image=image_tk)
        frame.canvas.image = image_tk

    def update_plot(self, mmdistance_x, mmdistance_y, mmdistance): #actively updates the plot as the new images are processed
        current_date = date.today()

        self.awayx_label.config(text = f'X Distance(mm): {mmdistance_x:.2f}')
        self.awayy_label.config(text = f'Y Distance(mm): {mmdistance_y:.2f}')
        self.totaldistance_label.config(text = f'Total Distance(mm): {mmdistance:.2f}')


    def save_data(self):
        # Initialize Tkinter root (necessary for the file dialog)
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        # Open a file dialog to choose the save location and filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Data As"
        )

        # Check if the user canceled the dialog
        if not filename:
            messagebox.showinfo("Save Data", "Save canceled.")
            return

        # Prepare the data for CSV
        headers = [
            'X Coord', 'Y Coord', 'Movement X (pixels)', 'Movement Y (pixel)',
            'Microns Moved X', 'Microns Moved Y', 'X DAC Value', 'Y DAC Value', 'Microns Per ADU X', 'Microns Per ADU Y', 'Detected Circle Radii (pixel)', 'Detected Pixel Size (microns/pixel)'
        ]

        # Prepare the data for CSV
        data_to_save = []
        num_entries = len(self.circle_centers)
        x_values = [x for x, y in self.circle_centers]
        y_values = [y for x, y in self.circle_centers]
        x_dacvalue = [x for x, y in self.dac_values]
        y_dacvalue = [y for x, y in self.dac_values]

        for i in range(num_entries):
            # Collect data for each row
            data_row = {
                'X Coord': x_values[i] if i < len(x_values) else "N/A",
                'Y Coord': y_values[i] if i < len(y_values) else "N/A",
                'Movement X (pixels)': self.movement_in_x[i] if i < len(self.movement_in_x) else "N/A",
                'Movement Y (pixel)': self.movement_in_y[i] if i < len(self.movement_in_y) else "N/A",
                'Microns Moved X': self.microns_moved_in_x[i] if i < len(self.microns_moved_in_x) else "N/A",
                'Microns Moved Y': self.microns_moved_in_y[i] if i < len(self.microns_moved_in_y) else "N/A",
                'X DAC Value': x_dacvalue[i] if i < len(x_dacvalue) else "N/A", 
                'Y DAC Value': y_dacvalue[i] if i < len(y_dacvalue) else "N/A",
                'Microns Per ADU X': self.microns_per_ADU_in_x[i] if i < len(self.microns_per_ADU_in_x) else "N/A",
                'Microns Per ADU Y': self.microns_per_ADU_in_y[i] if i < len(self.microns_per_ADU_in_y) else "N/A",
                'Detected Circle Radii (pixel)': self.circle_radii[i] if i < len(self.circle_radii) else "N/A",
                'Detected Pixel Size (microns/pixel)': self.pixle_size[i] if i < len(self.pixle_size) else "N/A"
            }
            
            data_to_save.append(data_row)

        # Write the data to the CSV file
        if data_to_save:
            try:
                with open(filename, 'w', newline='') as file:
                    writer = csv.DictWriter(file, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data_to_save)
                messagebox.showinfo("Save Data", f"Data successfully saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Data", f"Error saving data: {e}")

        root.destroy()  # Destroy the hidden root window after saving

# Make sure to include the rest of your class methods and initialization here

    def __del__(self):
        # Cleanup the camera on application close
        if hasattr(self, 'ser'):
            self.amp_off() # failsafe to make sure the preamp is always turned off when closing 
            self.ser.close()
        if hasattr(self, 'camera'):
            self.camera.close()
            #asi.exit()
            self.root.destroy() # Closes the Tkinter window and exits the application


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop() #runs the app


# Problems
    # the update plot does not keep the axis flipped after updating them 
    # the camera does not capture a photo on the first try and sometimes code needs to be rerun ----> patched but not fixed 
    # still have not gotten the DAC x and y values to go through, 4 arguements instead of three ----> fixed 
    # DAC values are not updated when the dac changes

# Zwo ASI mini specs 
    #Resolution : 1936 x 1096
    # 2.9 micron pixel size or 0.0029mm or 2.9e-6 m
    # 32 microsecond to 2000s exposure time
    # Focal Distace : 8.5mm or 0.0084m

# Gameplan 
    #find the calibration of the microns to pixles. we know the size of the clading, and cointed the pixle raduis
    #have the DAC go through a set of steps . X and Y values, take a step, wait, then take a picture and process it.\
    # continue this and save the x and y coordinates that are accociated with the DAC values 
    #find how much microns the fiber has moved from each step. find the microns/ADU(which is the 0-4095 number we inputted) for both x and y 
    
# How do we want to store data?
    # definetly in a csv file
    # I think it should keep track of all of the raw data it can 
    # we want: what element we are testing, x and y coordinates, DAC values set, x and y movements coorelated to the DAC set (both in pixles and in microns)
    
# size_of_fiber = 125e-6 # meters 
# magnification = camera_fiber_size / size_of_fiber
# image_distance = 2 # just putting in random numbers
# focal_length = .0084
# object_distance = (1/focal_length) * (1-(size_of_fiber/camera_fiber_size))
# print(object_distance)
