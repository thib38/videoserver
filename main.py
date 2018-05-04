import sys
import numpy as np
import logging
import traceback
import zmq
import cv2
import time
import socket
import pickle
from multiprocessing import Process, Pipe
import threading
import yaml


from PyQt5.QtCore import *  # crashes if not generic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QSizePolicy, QHeaderView, QFileSystemModel, QMessageBox, QMenu, QAction, \
    QLabel, QProgressBar, QDialog, QTableView, QButtonGroup, QFileDialog

from MainWindow import *


class ImageServer():
    """
    Initiatied in a separate Process
    - starts a zmq server
    - polls for image
    - send them to main process via the Pipe connection passed in parameter

    """

    def __init__(self, pipe_connection_child, tcp_port_listener=5555):
        self.tcp_port_listener = str(tcp_port_listener)
        self.pipe_connection = pipe_connection_child
        self.zmq_context = None
        self.zmq_socket_listener = None
        print("zmq server initiating...")
        self._launch_zmp_server()
        self._infinite_loop_get_image_and_queue_them(pipe_connection_child)

    def _launch_zmp_server(self):
        # get ip address of the hots running the program
        host_ip_address = socket.gethostbyname(socket.gethostname())   # TODO WORKS ONLY ON WINDOWS
        # start zmq listener
        self.zmq_context = zmq.Context()
        self.zmq_socket_listener = self.zmq_context.socket(zmq.REP)
        self.zmq_socket_listener.bind("tcp://" + host_ip_address + ":" + self.tcp_port_listener)
        return None

    def _infinite_loop_get_image_and_queue_them(self, pipe_connection_child):


        print("listener launched... ")
        while True:
            multipart_message = self.zmq_socket_listener.recv_multipart()
            camera_id, serialized_image = multipart_message
            # camera_id = int(camera_id_byte.decode('utf-8'))
            image_in_numpy_bgr_format = pickle.loads(serialized_image)
            print("Received image from %s" % str(camera_id))
            # forward message to main process
            pipe_connection_child.send([camera_id, image_in_numpy_bgr_format])
            #  Send reply back to client with same data
            self.zmq_socket_listener.send(b"ack")


class SetCameraQueryContext():
    """
    Send via zmq client queries to the camera associated to the instance
    """

    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.server_endpoint = "tcp://" + "192.168.1.27" + ":" + "5556"
        self.context = zmq.Context()
        self.client = self.context.socket(zmq.REQ)
        self.client.connect(self.server_endpoint)

    def send_test_query(self):
        self.client.send_json("test")
        if self.client.recv_json() == "ok":
            return(True)
        else:
            return(False)

    def set_capture_mode_to_motion_detection(self):
        self.client.send_json("capture_mode_set_to_motion_detection")
        if self.client.recv_json() == "ok":
            return (True)
        else:
            return (False)

    def set_capture_mode_to_all_frames(self):
        self.client.send_json("capture_mode_set_to_all_frames")
        if self.client.recv_json() == "ok":
            return (True)
        else:
            return (False)


class Controller(QMainWindow, Ui_MainWindow):

    # signal emitted when image server provide images to display
    # first value is the Camera_id
    # second one is the image to be displayed in XXXX format
    # display_video_signal = pyqtSignal(int, np.ndarray)
    display_video_signal = pyqtSignal(int, QPixmap)

    def __init__(self):
        super().__init__()

        # initialize ui
        self.setupUi(self)

        self.display_video_signal.connect(self.display_image)

        # pipe used to communicate with the process hosting zmq server that receives images from RaspberryPi
        self.pipe_connection_parent, self.pipe_connection_child = Pipe()

        # start thread that will wait for images from image server process and will trigger the
        # pyqtSignal display_video_signal that will call the display of th image on screen
        t = threading.Thread(target=self._thread_get_image_from_server_and_set_event,
                             args=(self.pipe_connection_parent, ))
        t.daemon = True
        t.start()
        print("receiving thread started...")

        # spawn ImageServer process:
        #  - that runs a zmq server that receives images from raspberryPi
        #  - and send images via the Pipe to the receiving thread in main
        # process (_thread_get_image_from_server_and_set_event)
        self.p = Process(target=ImageServer, args=(self.pipe_connection_child, 5555,))
        self.p.start()
        print("Image Server started...")

        # instruct camera initial display mode
        camera_id = 1
        self.camera_query = SetCameraQueryContext(camera_id)
        print(str(self.camera_query.set_capture_mode_to_motion_detection()))


    def _thread_get_image_from_server_and_set_event(self, pipe_connection_parent):

        def opencv_2_resized_qpixmap(img_cv2_bgr, size=None):
            """
            Transform an opencv image in Qpixmap and resize it if a size couple is provided
            :param img_cv2_bgr:
            :param size: None of (width, height)
            :return: qpixmap resized
            """
            if size is not None:
                width, height = size
                img_resized = cv2.resize(img_cv2_bgr, (width, height), interpolation=cv2.INTER_AREA)
            else:
                img_resized = img_cv2_bgr
            # BGR to RGB conversion
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            # create QT image
            image = QImage(img_rgb, img_rgb.shape[1],
                           img_rgb.shape[0], img_rgb.shape[1] * 3, QImage.Format_RGB888)
            qpixmap_ = QPixmap(image)

            return qpixmap_
        #infinite loop on receive from pipe that is filled by the image server process
        while True:
            message = pipe_connection_parent.recv()  # message format is [camera_id, image_in_numpy_bgr_format]
            print("received %s" % str(message))
            camera_id, image_in_numpy_bgr_format = message
            image_qpixmap = opencv_2_resized_qpixmap(image_in_numpy_bgr_format,(500,375))
            self.display_video_signal.emit(camera_id, image_qpixmap)

    def display_image(self, camera_id, image_in_qpixmap_format=None):    # [camera_id, image_in_numpy_bgr_format]
        print(int(camera_id))
        self.labelNW.setPixmap(image_in_qpixmap_format)


def exception_to_string(excp):
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=??
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__, excp)


def handle_uncaugth_exception(*exc_info):
    """
    This function will be subsituted to sys.except_hook standard function that is raised when ecxeptions are raised and
    not caugth by some try: except: block
    :param exc_info: (exc_type, exc_value, exc_traceback)
    :return: stop program with return code 1
    """
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(exc_info[1].__traceback__)  # add limit=??
    pretty = traceback.format_list(stack)
    text = ''.join(pretty) + '\n  {} {}'.format(exc_info[1].__class__, exc_info[1])
    # text = "".join(traceback.format_exception(*exc_info))
    logger.error("Unhandled exception: %s", text)
    sys.exit(1)
    
if __name__ == "__main__":
    # set-up logger before anything - two  handlers : one on console, the other one on file
    formatter = \
        logging.Formatter("%(asctime)s :: %(funcName)s :: %(levelname)s :: %(message)s")

    handler_file = logging.FileHandler("video.log", mode="a", encoding="utf-8")
    handler_console = logging.StreamHandler()

    handler_file.setFormatter(formatter)
    handler_console.setFormatter(formatter)

    handler_file.setLevel(logging.DEBUG)
    handler_console.setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # A D A P T   LOGGING LEVEL        H E R E
    logger.addHandler(handler_file)
    logger.addHandler(handler_console)

    sys.excepthook = handle_uncaugth_exception  # reassign so that log is fed with problem

    VERSION = "V0.0.1"
    PROGRAM_NAME = "VIDEO_DISPLAY"



    logger.info('=========  ' + PROGRAM_NAME + ' ' + VERSION + ' STARTED ===========')

    with open('videoserver.yaml', "r") as stream:
        try:
            print(yaml.load(stream))
        except yaml.YAMLError as exc:
            print(exc)

    # sys.exit(-1)

    try:
        app = QtWidgets.QApplication(sys.argv)
        ui = Controller()
        ui.show()
        sys.exit(app.exec_())
    except Exception:
        logger.exception("Exception caugth:")

