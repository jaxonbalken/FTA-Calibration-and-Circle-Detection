from tkinter import *
from PIL import Image, ImageTk
import zwoasi
import numpy as np
import sys
import cv2  # For YUV to RGB conversion

# Initialize Tkinter root window
root = Tk()
root.title("ZWO Camera Video Stream")

# Create a frame for the application
app = Frame(root, bg='white')
app.grid()

# Label to display the video feed
lmain = Label(app)
lmain.grid()

# Initialize ZWO ASI Camera
def initialize_camera():
    # Initialize the camera
    camera_list = zwoasi.ListCameras()
    
    if len(camera_list) == 0:
        print("No cameras found!")
        sys.exit()
    
    # Use the first available camera
    camera = zwoasi.Camera(camera_list[0])

    # Set the camera resolution to 1939x1096
    camera.SetResolution(1939, 1096)

    # Set camera exposure time (in microseconds)
    camera.set_control_value(zwoasi.ASI_EXPOSURE, 40000)  # Exposure: 40ms (40000 µs)
    
    # Set the camera's gain
    camera.set_control_value(zwoasi.ASI_GAIN, 60)  # Gain: 60
    
    # Set the brightness (typically a value between 0-100, but check your camera)
    camera.set_control_value(zwoasi.ASI_BRIGHTNESS, 1)  # Brightness: 1 (Minimal)

    # Enable continuous capture mode (you can remove or modify this if not necessary)
    camera.StartCapture()

    return camera

# Open the camera
camera = initialize_camera()

# Function to capture and display frames
def video_stream():
    # Capture a frame (this call is non-blocking, so it'll grab the latest frame when ready)
    frame_data = camera.GetData()  # Get image data from the camera

    if frame_data is None:
        print("Failed to capture frame.")
        return

    # Convert the frame data into a numpy array
    frame = np.array(frame_data, dtype=np.uint8)
    
    # Convert the frame from YUV to RGB (ZWO camera typically returns YUV)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_YUV2RGB)

    # Convert the frame to an Image object for Tkinter
    img = Image.fromarray(rgb_frame)
    imgtk = ImageTk.PhotoImage(image=img)
    
    # Update the label with the new image
    lmain.imgtk = imgtk
    lmain.configure(image=imgtk)
    
    # Call the video_stream function again after 10 ms
    lmain.after(10, video_stream)

# Start the video stream
video_stream()

# Gracefully close the window and release the camera
def on_close():
    camera.StopCapture()  # Stop the camera capture
    camera.Close()  # Close the camera properly
    root.destroy()  # Close the Tkinter window

root.protocol("WM_DELETE_WINDOW", on_close)  # Bind the close button to the on_close function

# Start the Tkinter main loop
root.mainloop()
