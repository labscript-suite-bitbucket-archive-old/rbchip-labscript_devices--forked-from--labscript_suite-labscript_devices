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

    def set_attributes(self, attr_dict):
        self.attributes.update(attr_dict)
        
    def set_attribute(self, name, value):
        self.attributes[name] = value

    def get_attribute_names(self, visibility_level, writeable_only=True):
        return list(self.attributes.keys())

    def get_attribute(self, name):
        return self.attributes[name]

    def snap(self):
        """Acquire a single image and return it"""
        self.configure_acquisition()
        self.camera.acquire()
        images = self.camera.download_acquisition()
        print(f'Actual exposure time was {self.camera.exposure_time}')
        return images[-1]

    def configure_acquisition(self, continuous=False, bufferCount=None):
        self.camera.setup_acquisition(self.attributes)

    def grab(self):
        """ Grab last/single image """
        img = self.snap()
        # Consider using run til abort acquisition mode...
        return img

    def grab_multiple(self, n_images, images, waitForNextBuffer=True):
        """Grab n_images into images array during buffered acquistion."""
    
        # Catch timeout errors, check if abort, else keep trying.
        
        print(f"Attempting to grab {n_images} acquisition(s).")
        for _ in range(n_images):
            self.camera.acquire()
            downloaded = self.camera.download_acquisition()
            images.append(downloaded)
            self.camera.armed = True
        self.camera.armed = False
        print(f"Got {len(images)} of {n_images} acquisition(s).")


    def stop_acquisition(self):
        pass

    def abort_acquisition(self):
        self.camera.abort_acquisition()
        self._abort_acquisition = True

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

