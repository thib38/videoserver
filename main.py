import sys
import logging
import traceback
import zmq
import cv2
import time
import socket
import pickle
from multiprocessing import Process, Pipe

from PyQt5.QtCore import *  # crashes if not generic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QSizePolicy, QHeaderView, QFileSystemModel, QMessageBox, QMenu, QAction, \
    QLabel, QProgressBar, QDialog, QTableView, QButtonGroup, QFileDialog

from MainWindow import *


class ImageServer():
    """
    Initiatied in a separate server
    - starts a zmq server
    - polls for image - send them to Image Controller

    """
    def __init__(self, pipe_connection_child, tcp_port_listener=5555):
        self.tcp_port_listener = str(tcp_port_listener)
        self.pipe_connection = pipe_connection_child
        self.zmq_context = None
        self.zmq_socket_listener = None
        print("zmq server initiating...")
        self._launch_zmp_server()
        self._infinite_loop_get_image_and_queue_them()

    def _launch_zmp_server(self):
        # get ip address of the hots running the program
        host_ip_address = socket.gethostbyname(socket.gethostname())
        # start zmq listener
        self.zmq_context = zmq.Context()
        self.zmq_socket_listener = self.zmq_context.socket(zmq.REP)
        self.zmq_socket_listener.bind("tcp://" + host_ip_address + ":" + self.tcp_port_listener)
        return None

    def _infinite_loop_get_image_and_queue_them(self):

        while True:
            multipart_message = self.zmq_socket_listener.recv_multipart()
            camera_id, serialized_image = multipart_message
            image_in_numpy_bgr_format = pickle.loads(serialized_image)
            print("Received image from %s" % str(camera_id))
            #  Send reply back to client with same data
            self.zmq_socket_listener.send(b"ack")
            # put message in the pipe
            self.pipe_connection.send([camera_id, image_in_numpy_bgr_format])


class ImageController():

    def __init__(self):

        # spawn ImageServer process
        # pipe used to communicate with the process hosting zmq server that receives images from RaspberryPi
        self.pipe_connection_parent, self.pipe_connection_child = Pipe()
        self.P = Process(target=ImageServer, args=(self.pipe_connection_child, 5555,))
        self.P.start()
        print("Image Server started...")

    def _thread_get_image_from_server_and_set_event(self):

        #infinite loop on receive from pipe that is filled by the image server process
        while True:
            message = self.pipe_connection_parent.recv()  # message format is [camera_id, image_in_numpy_bgr_format]
            # TODO store message in memory
            # TODO set an event that triggers display
            # TODO or call directly the display method ?



class Controller(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()

        # initialize ui
        self.setupUi(self)

        # start zmq server that receives images from raspberryPi in separate process

        ic = ImageController()


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


    try:
        app = QtWidgets.QApplication(sys.argv)
        ui = Controller()
        ui.show()
        sys.exit(app.exec_())
    except Exception:
        logger.exception("Exception caugth:")

