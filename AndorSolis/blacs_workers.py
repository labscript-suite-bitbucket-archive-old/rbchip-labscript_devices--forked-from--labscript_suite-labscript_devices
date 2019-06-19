#####################################################################
#                                                                   #
# /labscript_devices/AndorSolis/blacs_workers.py                    #
#                                                                   #
# Copyright 2019, Joint Quantum Institute                           #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker

class AndorCamera(object):

    def __init__(self):
        global AndorCam
        from .andor_sdk.andor_utils import AndorCam
        self.camera = AndorCam()
        self.added_acquisition_attrs = {}

    def set_attributes(self, attr_dict):
        self.added_acquisition_attrs = attr_dict

    def set_attribute(self, name, value):
        self.added_acquisition_attrs[name] = value

    def get_attribute_names(self, visibility_level, writeable_only=True):
        return list(self.added_acquisition_attrs.keys())

    def get_attribute(self, name):
        try: 
            self.added_acquisition_attrs[name]
        except NameError:
            self.camera.default_acquisition_attrs[name]

    def snap(self):
        self.camera.snap()

    def configure_acquisition(self, continous=True, bufferCount=3):
        self.camera.setup_acquisition(self.added_acquisition_attrs)

    def grab(self):
        return self.camera.grab_acquisition()

    def grab_multiple(self, n_images, images, waitForNextBuffer=True):
        return self.grab()

    def stop_acquisition(self):
        pass

    def abort_acquisition(self):
        self.camera.abort_acquisition()

    def _decode_image_data(self, img):
        pass

    def close(self):
        self.camera.shutdown()

class AndorSolisWorker(IMAQdxCameraWorker):

    interface_class = AndorCamera

