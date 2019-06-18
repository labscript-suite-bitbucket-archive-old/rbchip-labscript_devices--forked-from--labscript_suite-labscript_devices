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
from .andor_sdk.andor_utils import AndorCam

class AndorSolisWorker(IMAQdxCameraWorker):

    interface_class = AndorCam

    def get_attributes(self):
        return self.acquisition_attributes

    def set_attributes(self):
        pass

    def get_attribute_names(self):
        return self.acquisition_attributes.keys()

    def get_attribute(self):
        pass

    def configure_acquisition(self):
        pass

