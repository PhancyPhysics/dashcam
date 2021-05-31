# dashcam

## Synopsis

- Capture images or video from a webcam connected to a Raspberry Pi that receives commands from an Android Phone over BlueTooth
- Can be used to create timelapses or record car trips

## Commands

  __capture__ : Captures a single image
  
  __repeat [seconds]__ : Captures an image over a period defined in seconds. Default is 15 seconds.
  
  __setTime [seconds]__ : Sets the duration for a recurring image capture
  
  __stop__ : Stops recurring image capture
  
  __record__ : Starts a video recording
  
  __end__ : Ends a video recording
  
  __exit__ : Terminates dashcam
  
  __help__ : Returns this help message
 
## Requirements

- Python 3
- Raspberry Pi 3 (Tested on Model B V1.2)
- openCV's cv2 module
- pybluez's bluetooth module
- Serial bluetooth Terminal App (On Google Play)

## Additional Notes:

- On Raspberry Pi, add the following line to the root user's crontab: 
```
@reboot sleep 60 && usr/bin/python3 /home/pi/Documents/Projects/dashcam/dashcam.py >> ~/cron.log 2>&1
```
- This will execute the dashcam python script whenever the Raspberry Pi restarts. 
- Video is hardcoded to record at 1280 by 720 at 10 fps to preven the file size from exceeding the size of the USB drive used during testing. 
- Instructions on how bluetooth is enabled on the Raspberry Pi: https://raspberrypi.stackexchange.com/questions/45246/bluetooth-import-for-python-raspberry-pi-3
- Other helpful links in the DashCam_Notes_0.txt file. 
