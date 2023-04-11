import cv2
import os
import  threading
import signal
import sys
import time
from datetime import datetime
try:
    from  Queue import  Queue
except ModuleNotFoundError:
    from  queue import  Queue

os.environ["GST_DEBUG"] = "nvarguscamerasrc:5"

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    camera.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


def gstreamer_pipeline(
    capture_width=1920,
    capture_height=1080,
    display_width=1920,
    display_height=1080,
    framerate=60,
    flip_method=0,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

class FrameReader(threading.Thread):
    queues = []
    _running = True
    camera = None
    def __init__(self, camera, name):
        threading.Thread.__init__(self)
        self.name = name
        self.camera = camera
 
    def run(self):

        while self._running:
            _, frame = self.camera.read()
            while self.queues:
                queue = self.queues.pop()
                queue.put(frame)
            
    def addQueue(self, queue):
        self.queues.append(queue)

    def getFrame(self, timeout = None):
        queue = Queue(1)
        self.addQueue(queue)
        return queue.get(timeout=timeout)

    def stop(self):
        self._running = False   

class Camera(object):
    frame_reader = None
    cap = None

    def __init__(self):
        self.open_camera()

    def open_camera(self):
        self.cap = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera!")
        if self.frame_reader == None:
            self.frame_reader = FrameReader(self.cap, "")
            self.frame_reader.daemon = True
            self.frame_reader.start()

    def getFrame(self):
        try:
            return self.frame_reader.getFrame()
        except queue.Empty:
            print("Frame queue is empty")
            return None     

    def getFrameRate(self):
        counter = 0
        start_time = datetime.now()
        frame_count = 0
        start = time.time()
        while True:
            frame = self.frame_reader.getFrame()
            counter += 1
            frame_count += 1

            if time.time() - start >= 1:
                if sys.version[0] == '2':
                    print("fps: {}".format(frame_count))    
                else:
                    print("fps: {}".format(frame_count),end='\r')
                start = time.time()
                frame_count = 0 

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        avgtime = elapsed_time.total_seconds() / counter
        print ("Average time between frames: " + str(avgtime))
        print ("Average FPS: " + str(1/avgtime))

    def close(self):
        self.frame_reader.stop()
        self.cap.release()

if __name__ == "__main__":
    camera = Camera()
    camera.getFrameRate()
    time.sleep(10)
    camera.close()
