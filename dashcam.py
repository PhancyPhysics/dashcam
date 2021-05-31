"""
Synopsis:

    - Capture images or video from a WebCam connected to a Raspberry Pi that receives commands from an Android Phone over BlueTooth
    - Can be used to create timelapses or record car trips

Commands:
	
    capture : Captures a single image
	repeat [seconds] : Captures an image over a period defined in seconds. Default is 15 seconds.
	setTime [seconds] : Sets the duration for a recurring image capture
	stop : Stops recurring image capture
	record : Starts a video recording
	end : Ends a video recording
	exit : Terminates dashcam
	help : Returns this help message

Requirements: 

    - Python 3
    - Raspberry Pi 3 (Tested on Model B V1.2)
    - openCV's cv2 module
    - pybluez's bluetooth module
    - Serial bluetooth Terminal App (On Google Play)

Additional Notes:

    - On Raspberry Pi, add the following line to the root user's crontab: 
        @reboot sleep 60 && usr/bin/python3 /home/pi/Documents/Projects/dashcam/dashcam.py >> ~/cron.log 2>&1
    - This will execute the dashcam python script whenever the Raspberry Pi restarts. 
    - Video is hardcoded to record at 1280 by 720 at 10 fps to preven the file size from exceeding the size of the USB drive used during testing. 
    - Instructions on how bluetooth is enabled on the Raspberry Pi: https://raspberrypi.stackexchange.com/questions/45246/bluetooth-import-for-python-raspberry-pi-3
"""

import cv2
import bluetooth
import threading
import logging
from time import sleep
from datetime import datetime
from os import path, mkdir, getcwd, walk

FLASHDRIVENAME = '0410-673B' # Change this to match name assigned to USB drive when it is plugged into the Raspberry Pi.
ROOTDIR = '/media/pi/{0}/dashcam'.format(FLASHDRIVENAME) 
PORT = 1
EXITFLAG = False

class stoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(stoppableThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class cameraClass:
    def __init__(self, fileDir):
        self.cam = cv2.VideoCapture(0)
        self.cam.set(3,1280)
        self.cam.set(4,720)
        self.cam.set(5, 10)
        self.fileDir = fileDir
        self.cameraThread = stoppableThread(target=self.captureImage, daemon=True)
        self.cameraThread.start()

    def captureImage(self):
        while not self.cameraThread.stopped():
            if EXITFLAG:
                break
            self.ret, self.frame = self.cam.read()
        self.cam.release()
        MESSAGES.append('Image capture stopped\r\n')

    def saveImage(self):
        if self.ret:
            time = datetime.now()
            currentTime = time.strftime('%Y%m%d%H%M%S')
            currentTimeFormatted = time.strftime('%Y-%m-%d %H:%M:%S')
            imageName = self.fileDir +'/' + currentTime + '.png'
            cv2.imwrite(imageName, self.frame)
            logging.debug('Image Saved: {0}'.format(imageName))
            MESSAGES.append('Image captured @ {0} \r\n'.format(currentTimeFormatted))

    def stopCapture(self):
        if self.cameraThread.isAlive():
            self.cameraThread.stop()    

class repeatClass:
    def __init__(self, cameraClass, sleepTime):
        self.camera = cameraClass
        self.sleepTime = sleepTime
        self.repeatThread = stoppableThread(target=self.captureImageRepeat, daemon=True)
        self.repeatThread.start()

    def captureImageRepeat(self):
        while not self.repeatThread.stopped():
            if EXITFLAG:
                break
            self.camera.saveImage()
            sleep(self.sleepTime)
        MESSAGES.append('Recurring image capture stopped\r\n')
            
    def stopRepeat(self):
        if self.repeatThread.isAlive():
            self.repeatThread.stop()

    def setSleepTime(self, time):
        self.sleepTime = time

class captureVideoClass:
    def __init__(self, fileDir):
        self.fileDir = fileDir
        self.videoThread = stoppableThread(target=self.captureVideo, args=(self.fileDir,), daemon=True)
        self.videoThread.start()

    def captureVideo(self, fileDir):
        cam = cv2.VideoCapture(0)
        cam.set(3,1280)
        cam.set(4,720)
        cam.set(5, 20)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        time = datetime.now()
        currentTime = time.strftime('%Y%m%d%H%M%S')
        currentTimeFormatted = time.strftime('%Y-%m-%d %H:%M:%S')
        videoFileName = fileDir + '/' + currentTime + '.avi'
        out = cv2.VideoWriter(videoFileName,fourcc, 10.0, (1280,720))
        MESSAGES.append('Recording Video @ {0} \r\n'.format(currentTimeFormatted))
        while not self.videoThread.stopped():
            ret, frame = cam.read()
            if ret:
                out.write(frame)
        cam.release()
        out.release()
        time = datetime.now()
        currentTimeFormatted = time.strftime('%Y-%m-%d %H:%M:%S')
        MESSAGES.append('Ending Recording @ {0} \r\n'.format(currentTimeFormatted))
            
    def stopVideo(self):
        if self.videoThread.isAlive():
            self.videoThread.stop()

class parseCommandClass:
    def __init__(self, port):
        self.server_socket=bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.server_socket.bind(("",port))
        self.server_socket.listen(1)
        logging.debug('Waiting for connection with client')
        (self.client_socket, self.address) = self.server_socket.accept()
        logging.debug('Accepted connection from {0}'.format(self.address))
        self.sendMessage('dashcam initiated. Welcome!')
        self.commandThread = stoppableThread(target=self.parseCommand, args=(self.client_socket,), daemon=True)
        self.commandThread.start()

    def parseCommand(self, client_socket):
        while not self.commandThread.stopped():
            if EXITFLAG:
                break
            rawData = client_socket.recv(1024)
            mungedData = rawData.decode("utf-8").rstrip()
            COMMANDS.append(mungedData)
            
    def stopListening(self):
        if self.commandThread.isAlive():
            self.commandThread.stop()

    def sendMessage(self, message):
        self.client_socket.send(message)

## Main

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(level=logging.ERROR)
logFileName = '{0}/dashcam.log'.format(getcwd())
logging.basicConfig(level=logging.DEBUG, filename=logFileName, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
# Check to see if ROOTDIR exists (if the USB drive is inserted) before beginning video capture
if path.exists(ROOTDIR):
    # Create current date folder if it does not already exists
    currentDateDir = '{0}/{1}'.format(ROOTDIR, datetime.now().strftime('%Y%m%d'))
    if not path.exists(currentDateDir):
        mkdir(currentDateDir)
    # Create a new session directory
    dirList = [curDir[0] for curDir in walk(currentDateDir)][1:]
    sessionDir = '{0}/Session_{1}'.format(currentDateDir, str(len(dirList)))
    mkdir(sessionDir)
    COMMANDS = []
    MESSAGES = []
    commandThread = parseCommandClass(PORT)
    cameraThread = cameraClass(sessionDir)
    captureThreads = []
    repeatThreads = []
    videoThreads = []
    repeatFlag = False
    while not EXITFLAG:
        # Collect commands inputed from phone and execute in FIFO order. 
        logging.debug('Command List: {0}'.format(COMMANDS))
        COMMANDS.reverse()
        while COMMANDS:
            curCommand = COMMANDS.pop(0)
            if curCommand == 'capture':
                if not videoThreads:
                    cameraThread.saveImage()
                else:
                    MESSAGES.append('Cannot capture images while video is recording. Use \'end\' to end video recording.\r\n')
            if curCommand.split(' ')[0] == 'repeat':
                if not videoThreads:
                    if not repeatThreads:
                        if len(curCommand.split(' ')) > 1:
                            time = int(curCommand.split(' ')[1])
                        else:
                            time = 15
                        repeatThreads.append(repeatClass(cameraThread, time))
                        MESSAGES.append('Recurring image capture started. Duration set to: {0} seconds\r\n'.format(str(time)))
                    else:
                        MESSAGES.append('Recurring image capture already started. Use \'stop\' or \'setTime\' to modify.\r\n')
                else:
                    MESSAGES.append('Cannot capture images while video is recording. Use \'end\' to end video recording.\r\n')
            if curCommand.split(' ')[0] == 'setTime':
                if repeatThreads:
                    if len(curCommand.split(' ')) > 1:
                        time = int(curCommand.split(' ')[1])
                    else:
                        time = 15
                    repeatThreads[0].setSleepTime(time)
                    logging.debug('Recurring image capture duration set to: {0} seconds'.format(str(time)))
                    MESSAGES.append('Recurring image capture duration set to: {0} seconds\r\n'.format(str(time)))
            if curCommand == 'stop':
                while repeatThreads:
                    curThread = repeatThreads.pop(0)
                    curThread.stopRepeat()
            if curCommand == 'record':
                if not repeatThreads and not captureThreads:
                    if not videoThreads:
                        videoThreads.append(captureVideoClass(sessionDir))
                    else:
                        MESSAGES.append('Video already recording. Use \'end\' to end the recording.\r\n')
                else:
                    MESSAGES.append('Cannot record video while image is being captured.\r\n')
            if curCommand == 'end':
                while videoThreads:
                    curThread = videoThreads.pop(0)
                    curThread.stopVideo()
            if curCommand == 'exit':
                while repeatThreads:
                    curThread = repeatThreads.pop(0)
                    curThread.stopRepeat()
                while videoThreads:
                    curThread = videoThreads.pop(0)
                    curThread.stopVideo()
                cameraThread.stopCapture()
                EXITFLAG = True
            if curCommand == 'help':
                MESSAGES.append('Synopsis: Capture images or video from Raspberry Pi Webcam using Android Phone over BlueTooth\r\n'
                                + 'Commands: \r\n'
                                + 'capture : Captures a single image\r\n'
                                + 'repeat [seconds] : Captures an image over a period defined in seconds. Default is 15 seconds.\r\n'
                                + 'setTime [seconds] : Sets the duration for a recurring image capture\r\n'
                                + 'stop : Stops recurring image capture\r\n'
                                + 'record : Starts a video recording\r\n'
                                + 'end : Ends a video recording\r\n'
                                + 'exit : Terminates dashcam\r\n'
                                + 'help : Returns this help message\r\n'
                )
        logging.debug('captureThreads length: {0}'.format(len(captureThreads)))
        while MESSAGES:
            curMessage = MESSAGES.pop(0)
            commandThread.sendMessage(curMessage)       
        #sleep(1)
    commandThread.sendMessage('Terminating dashcam. GoodBye! \r\n')
    commandThread.stopListening()
    logging.debug('dashcam Successfully Terminated')
else:
    logging.debug('USB drive not found. dashcam Terminated')

# Main Loop 
    # Spin up Listener thread; This thread listens for instructions from phone
    # Spin up new thread based on instructions received: 
    #   Repeat Thread: Capture image periodically until a stop instruction is received
    #   Capture Thread: Capture a single image and then terminate the thread