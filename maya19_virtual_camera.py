# This script copyrights belong to 3deep.org and the used solutions authors as mentioned.
# And it's available for academic and non-commercial use only.

import shiboken2
import maya.cmds as mc
import pymel.core as pmc
import maya.OpenMayaUI as mui
from PySide2 import QtWidgets, QtCore

import cv2
import socket
import numpy as np

from pywin32.win32 import win32gui, win32api
from pywin32.win32.lib import win32con
from pywin32.pythonwin import win32ui

OBJECT_NAME = "3Deep Virtual Camera"

class VirtualCamera_3Deep(QtWidgets.QWidget):

    def __init__(self, parent=None):

        super(VirtualCamera_3Deep, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setObjectName(OBJECT_NAME)
        self.setWindowTitle(OBJECT_NAME) 

        self.udp_ip = "192.168.0.0"
        self.udp_port = "27005"
        self.local_ip = socket.gethostbyname(socket.gethostname())

        self.stream_toggle = False
        self.stream_viewport = False

        self.init_ar_camera()
        self.init_widgets()
        self.init_sockets()

    def init_ar_camera(self):

        self.ar_camera = mc.camera(name="[3deep]_ar_camera")
        mc.xform(self.ar_camera, matrix = mc.xform("persp", query=True, matrix=True))

    def init_sockets(self):

        self.udp_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16384)

    def toggle_stream(self):

        self.stream_toggle = not self.stream_toggle
        
        if self.stream_toggle:

            self.udp_ip = self.ip_lineedit.text()
            self.udp_port = int(self.port_lineedit.text())

            # now open a new TCP port
            cmds.commandPort(name="{0}:{1}".format(self.local_ip, self.udp_port), sourceType="python")
            print("Connection established")

            self.thread_timer.start()
            self.stream_btn.setText("Stop Stream")
            self.stream_btn.setStyleSheet("color:black; background-color: #DC143C")

        else:

            # if it was already opened under another configuration
            cmds.commandPort(name="{0}:{1}".format(self.local_ip, self.udp_port), close=True)
            print("Connection closed")

            self.thread_timer.stop()
            self.stream_btn.setText("Start Stream")
            self.stream_btn.setStyleSheet("color:black; background-color: #ADFF2F")

    def stream(self):

        if all([self.stream_toggle and self.stream_viewport]):
            
            img = self.grab_screen([self.pos().x()+25, self.pos().y()+65, self.pos().x()+self.size().width()+125, self.pos().y()+self.size().height()+90])
            img = cv2.resize(img, (640,360))
            img_str = cv2.imencode('.jpg', img)[1].tostring()
            self.udp_socket.sendto(img_str,(self.udp_ip, self.udp_port))

    def toggle_viewport_stream(self, state):
        
        self.stream_viewport = state

    def init_widgets(self):

        qt_layout = QtWidgets.QVBoxLayout(self)
        qt_layout.setObjectName('viewportLayout') 
        mc.setParent('viewportLayout')

        pane_layout = mc.paneLayout()            
        model_panel = mc.modelPanel("embeddedModelPanel#", cam=self.ar_camera[0])

        ptr = mui.MQtUtil.findControl(pane_layout)
        paneLayoutQt = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)

        stream_layout = QtWidgets.QVBoxLayout()
        ip_port_layout = QtWidgets.QHBoxLayout()
        self.ip_lineedit = QtWidgets.QLineEdit(self.udp_ip)
        self.port_lineedit = QtWidgets.QLineEdit(self.udp_port)
        self.port_lineedit.setMaximumWidth(60)
        
        self.stream_viewport_cb = QtWidgets.QCheckBox("Stream Viewport")
        self.stream_viewport_cb.stateChanged.connect(self.toggle_viewport_stream)

        ip_port_layout.addWidget(QtWidgets.QLabel("IP Address:"))
        ip_port_layout.addWidget(self.ip_lineedit)
        ip_port_layout.addWidget(QtWidgets.QLabel("Port:"))
        ip_port_layout.addWidget(self.port_lineedit)
        ip_port_layout.addWidget(self.stream_viewport_cb)

        self.stream_btn = QtWidgets.QPushButton("Start Stream")
        self.stream_btn.clicked.connect(self.toggle_stream)
        self.stream_btn.setStyleSheet("color:black; background-color: #ADFF2F")

        stream_layout.addLayout(ip_port_layout)
        stream_layout.addWidget(self.stream_btn)

        qt_layout.addWidget(paneLayoutQt)
        qt_layout.addLayout(stream_layout)

        self.thread_timer = QtCore.QTimer()
        self.thread_timer.timeout.connect(self.stream)

        self.setFixedSize(640, 360)

    def closeEvent(self, e):
        
        mc.delete(self.ar_camera)

    def grab_screen(self, region=None):
        # this snppit of code was taken from sentdex GTA ML project.

        hwin = win32gui.GetDesktopWindow()
    
        if region:
                left,top,x2,y2 = region
                width = x2 - left + 1
                height = y2 - top + 1
        else:
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    
        hwindc = win32gui.GetWindowDC(hwin)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
        
        signedIntsArray = bmp.GetBitmapBits(True)
        img = np.fromstring(signedIntsArray, dtype='uint8')
        img.shape = (height,width,4)
    
        srcdc.DeleteDC()
        memdc.DeleteDC()
        win32gui.ReleaseDC(hwin, hwindc)
        win32gui.DeleteObject(bmp.GetHandle())
    
        return img

def start_virtual_camera():
    maya_window = pmc.ui.Window("MayaWindow").asQtObject()

    if mc.window(OBJECT_NAME, exists=True):
        mc.deleteUI(OBJECT_NAME)

    vc = VirtualCamera_3Deep(parent = maya_window)
    vc.show()

start_virtual_camera()