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

from labscript_devices.IMAQdxCamera.blacs_workers import MockCamera, IMAQdxCameraWorker

class AndorCamera(object):

    def __init__(self):
        global AndorCam
        from .andor_sdk.andor_utils import AndorCam
        self.camera = AndorCam()
        self.attributes = self.camera.default_acquisition_attrs

    def setup(self):
        self.camera.setup_acquisition(self.attributes)

    def set_attributes(self, attr_dict):
        self.attributes.update(attr_dict)
        
    def set_attribute(self, name, value):
        self.attributes[name] = value

    def get_attribute_names(self, visibility_level, writeable_only=True):
        return list(self.attributes.keys())

    def get_attribute(self, name):
        return self.attributes[name]

    def snap(self):
        self.setup()
        self.camera.snap()
        return self.camera.grab_acquisition()

    def configure_acquisition(self, continous=True, bufferCount=3):
        self.camera.setup_acquisition()

    def grab(self):
        return self.snap()

    def grab_multiple(self, n_images, images, waitForNextBuffer=True):
        pass

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

    def get_camera(self):
        """ Andor cameras may not be specified by serial numbers"""
        if self.mock:
            return MockCamera()
        else:
            return self.interface_class()
            
    def get_attributes_as_dict(self, visibility_level):
        """Return a dict of the attributes of the camera for the given visibility
        level"""
        return self.camera.attributes

