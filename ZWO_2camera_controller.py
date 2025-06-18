"""
Code for simultaneous reads of 2 ZWO cameras. Assume they are named 'A' and 'B'
"""
import numpy as np
import time
import matplotlib
import matplotlib.pyplot as plt
import csv
import os
from tkinter import *
from time import sleep
import ctypes.wintypes
import zwoasi as asi
import sys
import h5py

from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  NavigationToolbar2Tk) 
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.cm as cm
import ctypes.wintypes


global camera1,camera2,num_cameras
num_cameras=0
camera1 = 0
camera2 = 1

default_params={}
default_params['rate']=100
default_params['n_frames']=10000
default_params['roi_size']=64
default_params['TXT_prefix']='2cam_'
default_params['Folder']='/zwo_2cam'

paramstxt=['Frame_Rate','n_frames','roi_size_8','File_prefix','Folder']
paramskeys=paramstxt

window = Tk()
window.title("Dual ZWO camera control")
window.geometry('800x1300')   


def utcnow_microseconds():
    system_time = ctypes.wintypes.FILETIME()
    #system call used by time.time()
    #ctypes.windll.kernel32.GetSystemTimeAsFileTime(ctypes.byref(system_time))
    #getting high precision:
    ctypes.windll.kernel32.GetSystemTimePreciseAsFileTime(ctypes.byref(system_time))
    large = (system_time.dwHighDateTime << 32) + system_time.dwLowDateTime
    return large // 10 - 11644473600000000

def get_date_filename(folder,text_string):
    '''default filename using date and time. 
    creates a directory for each day and returns the file string to be used'''    
    now=time.localtime()[0:6]
    dirfmt = "%4d_%02d_%02d"
    dirname = folder+'\\'+dirfmt % now[0:3]
    filefmt = "%02d_%02d_%02d.h5"
    filename= text_string+filefmt % now[3:6]
    ffilename=os.path.join(dirname,filename)
    print('dirname',dirname)
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    return(ffilename) 

def get_time_filename(folder,text_string):
    '''default filename using date and time. 
    creates a directory for each day and returns the file string to be used'''    
    now=time.localtime()[0:6]
    filefmt = "%02d_%02d_%02d.h5"
    filename= text_string+filefmt % now[3:6]
    ffilename=os.path.join(folder,filename)
    print(ffilename)
    return(ffilename) 

def get_date_dirname():
    '''default directory using date and time. 
    creates a directory for each day and returns '''    
    now=time.localtime()[0:6]
    dirfmt = "%4d_%02d_%02d"
    dirname = dirfmt % now[0:3]
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    return(dirname)     
    
def connect_cams_callback():
        #set asi init check how many cameras, connect them, get IDs and populate cam parameters ID, EXP, gain
        global camera1,camera2,num_cameras
        global fig,ax1,ax2,canvas,im1p,im2p,im1,im2
        env_filename=os.getenv('ZWO_ASI_LIB')
        asi.init('C:\\Users\\ASE\\Desktop\\Ari Lab-2023\\Pics\\ASIStudio\\ASICamera2.dll')
        num_cameras = asi.get_num_cameras()
        print(num_cameras,' Cameras')
        camera1=asi.Camera(0)
        camera1.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1)
        camera1.set_roi()
        cam1_id = camera1.get_id()
        entry_cam1_id.insert(END,str(cam1_id))      
        cam1_gain,jnk=camera1.get_control_value(asi.ASI_GAIN)
        entry_cam1_gain.insert(END,str(cam1_gain))
        cam1_exposure,jnk=camera1.get_control_value(asi.ASI_EXPOSURE)
        entry_cam1_exp.insert(END,str(cam1_exposure))
        if num_cameras==2:
                camera2=asi.Camera(1)
                camera2.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1)
                camera2.set_roi()
                cam2_id = camera2.get_id()
                entry_cam2_id.insert(END,str(cam2_id))      
                cam2_gain,jnk=camera2.get_control_value(asi.ASI_GAIN)
                entry_cam2_gain.insert(END,str(cam2_gain))
                cam2_exposure,jnk=camera2.get_control_value(asi.ASI_EXPOSURE)
                entry_cam2_exp.insert(END,str(cam2_exposure))
        #get an image from each camera and make and populate the figures
        im1=camera1.capture()

        if num_cameras==2:
                 im2=camera2.capture()

        fig,(ax1,ax2) = plt.subplots(2,1,figsize=[4,6])
        ax1.title.set_text(cam1_id)
        im1p = ax1.imshow(im1, cmap=cm.Greys_r)
        if num_cameras==2:
                ax2.title.set_text(cam2_id)
                im2p = ax2.imshow(im2, cmap=cm.Greys_r)
        # creating the Tkinter canvas 
        # containing the Matplotlib figure 
        canvas = FigureCanvasTkAgg(fig, master = window)   
        canvas.draw() 
        # placing the canvas on the Tkinter   window 
        canvas.get_tk_widget().pack(side='top')
            # creating the Matplotlib toolbar 
        toolbar = NavigationToolbar2Tk(canvas, window) 
        toolbar.update() 
        # placing the toolbar on the Tkinter window 
        canvas.get_tk_widget().pack(side='top') 
        print('Camera Connected')
        
        return 
        
def set_cam_params_callback():
        #use IDs to set parameters on cameras from entry boxes
        #check ID to see if it connected
        global camera1,camera2,num_cameras
        if entry_cam1_id.get() !='':
                cam1_exposure = int(entry_cam1_exp.get())
                cam1_gain = int(entry_cam1_gain.get())
                print(cam1_exposure,cam1_gain)
                camera1.set_control_value(asi.ASI_EXPOSURE,cam1_exposure)
                camera1.set_control_value(asi.ASI_GAIN,cam1_gain)
                print(camera1.get_control_value(asi.ASI_GAIN))
        if entry_cam2_id.get() !='':
                cam2_exposure = int(entry_cam2_exp.get())
                cam2_gain = int(entry_cam2_gain.get())
                camera2.set_control_value(asi.ASI_EXPOSURE,cam2_exposure)
                camera2.set_control_value(asi.ASI_GAIN,cam2_gain)
        return

def oneshot_callback():
        #single shot from each camera, display both in Tk embedded window, use previously created fig,ax,canvas
        global camera1,camera2,num_cameras
        global fig,ax1,ax2,canvas
        global im1p,im2p
        im1=camera1.capture()
        im1p = ax1.imshow(im1, cmap=cm.Greys_r)
        if num_cameras==2:
                im2=camera2.capture()
                im2p = ax2.imshow(im2, cmap=cm.Greys_r)
        canvas.draw() 
        return

def init():
        global im1p,im2p,im1,im2,num_cameras
        im1p.set_data(im1)
        if num_cameras==2:
                im2p.set_data(im2)
        return

def animate_func(i):
        global camera1,camera2,num_cameras
        global fig,ax1,ax2,canvas
        global im1p,im2p
        im1=camera1.capture()
        im1p.set_data(im1)
        if num_cameras==2:
                im2=camera2.capture()
                im2p.set_data(im2)
        return 

def manyshot_callback():
        #acquire many shots from each camera, display both in Tk embedded window, use previously created fig,ax,canvas
        global fig,ax1,ax2,canvas,anim
        anim=animation.FuncAnimation(fig,animate_func,init_func=init,frames=1000,interval=10)
        canvas.draw()
        return
        
def manyshot_stop_callback():
        #stop the continuous acquire and plot
        global anim
        anim.event_source.stop()
        return


def quit_callback():
        global camera1,camera2,num_cameras
        if num_cameras>0:
                camera1.close()
        if num_cameras==2:
                camera2.close()
        exit()

def start_measurement_callback():
        rate=int(entry_rate.get())
        irate=1e6/rate
        nframes = int(entry_nframes.get())
        roisize=int(entry_roisize.get())
        global camera1,camera2,num_cameras
        global fig,ax1,ax2,canvas
        #first get an image from each camera, check for brightest pixel and see if ROIxROI fits around it
        #make sure it's full frame first
        camera1.set_roi()
        im1 = camera1.capture()
        max_y,max_x = im1.shape
        print('max_y,max_x',max_y,max_x)
        maxpix1 = np.unravel_index(np.argmax(im1, axis=None), im1.shape)
        start_x = int(maxpix1[1] - roisize/2)
        start_y = int(maxpix1[0] - roisize/2)
        if ((start_x<0) or(start_y<0) or ((start_x+roisize)>max_x) or ((start_y + roisize) > max_y)):
                #roi outside image
                start_x=int(max_x/2 - roisize/2)
                start_y=int(max_y/2 - roisize/2)
        print('cam1 startx,y,roisize',start_x,start_y,roisize)
        camera1.set_roi(start_x=start_x,start_y=start_y,width=roisize,height=roisize)
        camera1.start_video_capture()
        cam1_images=[]

        if num_cameras==2:
                camera2.set_roi()
                im2 = camera2.capture()
                max_y,max_x = im2.shape
                print('max_y,max_x',max_y,max_x)
                maxpix2 = np.unravel_index(np.argmax(im2, axis=None), im2.shape)
                start_x = int(maxpix2[1] - roisize/2)
                start_y = int(maxpix2[0] - roisize/2)
                if ((start_x<0) or(start_y<0) or ((start_x+roisize)>max_x) or ((start_y + roisize) > max_y)):
                        #if roi is outside image
                        start_x=int(max_x/2 - roisize/2)
                        start_y=int(max_y/2 - roisize/2)
                print('cam2 startx,y',start_x,start_y)
                camera2.set_roi(start_x=start_x,start_y=start_y,width=roisize,height=roisize)
                camera2.start_video_capture()
                cam2_images=[]
        
        
        t_start=time.time()
        tstart=utcnow_microseconds()

        for i in range(nframes):
                tlast=utcnow_microseconds()
                im1=camera1.capture_video_frame(timeout=1000)
                cam1_images.append(im1)
                
                if num_cameras==2:
                        im2=camera2.capture_video_frame(timeout=1000)
                        cam2_images.append(im2)
                while(utcnow_microseconds()-tlast)<irate:
                        continue

        t_stop=time.time()
        actual_rate = nframes/(t_stop-t_start)
        print('actual rate: ',actual_rate)
        camera1.stop_video_capture()
        if num_cameras==2:
                camera2.stop_video_capture()
        outdict={}
        outdict['cam_'+entry_cam1_id.get()+'_images']=cam1_images
        if num_cameras==2:
                outdict['cam_'+entry_cam2_id.get()+'_images']=cam2_images
        outdict['rate']=actual_rate
        #save to file
        folder=entry_folder.get()
        prefix=entry_prefix.get()
        filename=get_date_filename(folder,prefix)
        print(filename)
        save_dict_to_h5(outdict,filename=filename)
        return
        
def save_dict_to_h5(ddict,filename='star_images.h5', initialdir="../zwo_2cam"):
    #use group with attributes to mock up dictionary, save to h5 file 'h5f'
    #h5file=initialdir+'\\'+filename
    h5file = filename
    keys=ddict.keys()
    with h5py.File(h5file,'w') as h5f:
        for key in keys:
            h5f.create_dataset(key,data=np.array(ddict[key]))
        h5f.close()

settings_label=Label(window,text='Camera settings',font = "Helvetica 14 bold")
settings_label.pack(side=TOP)

paramstxt=['Frame_Rate','n_frames','roi_size_8','File_prefix','Folder']
paramskeys=paramstxt      

quit_button=Button(window,command=quit_callback)
quit_button.configure(text='QUIT',background='red',foreground='white',padx=50,font = "Helvetica 12 bold")
quit_button.pack(side=TOP) 

cam_connect_button=Button(window,command=connect_cams_callback)
cam_connect_button.configure(text='Connect cameras',background='blue',foreground='white',padx=50,font = "Helvetica 12 bold")
cam_connect_button.pack(side=TOP) 

fcams=Frame(window)
label_cam1=Label(fcams,text='Cam 1 ')
label_cam1.pack(side="left")
label_cam2=Label(fcams,text='Cam 2 ')
label_cam2.pack(side="right")
fcams.pack(side=TOP)

fids=Frame(window)
label_id=Label(fids,text='ID  ')
label_id.pack(side="left")
entry_cam1_id=Entry(fids)
entry_cam1_id.insert(END,'')
entry_cam1_id.configure(width=10)
entry_cam1_id.pack(side="left")

entry_cam2_id=Entry(fids)
entry_cam2_id.insert(END,'')
entry_cam2_id.configure(width=10)
entry_cam2_id.pack(side="right")
fids.pack(side=TOP)

fexp=Frame(window)
label_exp=Label(fexp,text='Exp(us)')
label_exp.pack(side="left")
entry_cam1_exp=Entry(fexp)
entry_cam1_exp.insert(END,'')
entry_cam1_exp.configure(width=10)
entry_cam1_exp.pack(side="left")

entry_cam2_exp=Entry(fexp)
entry_cam2_exp.insert(END,'')
entry_cam2_exp.configure(width=10)
entry_cam2_exp.pack(side="right")
fexp.pack(side=TOP)

fgain=Frame(window)
label_gain=Label(fgain,text='Gain   ')
label_gain.pack(side="left")
entry_cam1_gain=Entry(fgain)
entry_cam1_gain.insert(END,'')
entry_cam1_gain.configure(width=10)
entry_cam1_gain.pack(side="left")

entry_cam2_gain=Entry(fgain)
entry_cam2_gain.insert(END,'')
entry_cam2_gain.configure(width=10)
entry_cam2_gain.pack(side="right")
fgain.pack(side=TOP)

cam_set_button=Button(window,command=set_cam_params_callback)
cam_set_button.configure(text='Set camera params',background='blue',foreground='white',padx=50,font = "Helvetica 12 bold")
cam_set_button.pack(side=TOP) 


oneshot_button=Button(window,command=oneshot_callback)
oneshot_button.configure(text='Single shot',background='green',foreground='white',padx=50,font = "Helvetica 12 bold")
oneshot_button.pack(side=TOP) 

fmany=Frame(window)
manyshot_button=Button(fmany,command=manyshot_callback)
manyshot_button.configure(text='Many shot start',background='purple',foreground='white',padx=50,font = "Helvetica 12 bold")
manyshot_button.pack(side='left') 
manyshot_stop_button=Button(fmany,command=manyshot_stop_callback)
manyshot_stop_button.configure(text='Stop Many',background='red',foreground='white',padx=50,font = "Helvetica 12 bold")
manyshot_stop_button.pack(side='right') 
fmany.pack(side=TOP)



frate=Frame(window)
labelrate=Label(frate,text='Target rate')
labelrate.pack(side="left")
entry_rate=Entry(frate)
entry_rate.insert(END,100)
entry_rate.configure(width=10)
entry_rate.pack(side="left")
frate.pack(side=TOP)

fnframes=Frame(window)
labelnframes=Label(fnframes,text='Number of frames')
labelnframes.pack(side="left")
entry_nframes=Entry(fnframes)
entry_nframes.insert(END,1000)
entry_nframes.configure(width=10)
entry_nframes.pack(side="left")
fnframes.pack(side=TOP)

froisize=Frame(window)
labelroisize=Label(froisize,text='ROI size (multiple of 8, min 32)')
labelroisize.pack(side="left")
entry_roisize=Entry(froisize)
entry_roisize.insert(END,128)
entry_roisize.configure(width=10)
entry_roisize.pack(side="left")
froisize.pack(side=TOP)

fprefix=Frame(window)
labelprefix=Label(fprefix,text='File prefix')
labelprefix.pack(side="left")
entry_prefix=Entry(fprefix)
entry_prefix.insert(END,'zwo_2cam_')
entry_prefix.configure(width=10)
entry_prefix.pack(side="left")
fprefix.pack(side=TOP)

ffolder=Frame(window)
labelfolder=Label(ffolder,text='Folder')
labelfolder.pack(side="left")
entry_folder=Entry(ffolder)
entry_folder.insert(END,'./zwo_2cam')
entry_folder.configure(width=50)
entry_folder.pack(side="left")
ffolder.pack(side=TOP)



start_measurement_button=Button(window,command=start_measurement_callback)
start_measurement_button.configure(text='Start acquisition',background='Green',foreground='white',padx=50,font = "Helvetica 12 bold")
start_measurement_button.pack(side=TOP) 
 




 
window.mainloop()

