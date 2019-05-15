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
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from blacs.tab_base_classes import Worker

import labscript_utils.h5_lock
import h5py

import labscript_utils.properties

from labscript_utils import check_version

check_version('zprocess', '2.12.0', '3')

class MockCamera(object):
    """Mock camera class that returns fake image data."""

    def __init__(self):
        self.attributes = {}

    def set_attributes(self, attributes):
        self.attributes.update(attributes)

    def get_attribute(self, name):
        return self.attributes[name]

    def get_attribute_names(self, visibility_level=None):
        return list(self.attributes.keys())

    def configure_acquisition(self, continuous=False, bufferCount=5):
        pass

    def grab(self):
        return self.snap()

    def grab_multiple(self, n_images, images, waitForNextBuffer=True):
        print(f"Attempting to grab {n_images} (mock) images.")
        for i in range(n_images):
            images.append(self.grab())
            print(f"Got (mock) image {i+1} of {n_images}.")
        print(f"Got {len(images)} of {n_images} (mock) images.")

    def snap(self):
        N = 500
        A = 500
        x = np.linspace(-5, 5, 500)
        y = x.reshape((N, 1))
        clean_image = A * (1 - 0.5 * np.exp(-(x ** 2 + y ** 2)))

        # Write text on the image that says "NOT REAL DATA"
        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.load_default()
        canvas = Image.new('L', [N // 5, N // 5], (0,))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 20), "NOT REAL DATA", font=font, fill=1)
        clean_image += 0.2 * A * np.asarray(canvas.resize((N, N)).rotate(20))
        return np.random.poisson(clean_image)

    def stop_acquisition(self):
        pass

    def abort_acquisition(self):
        pass

    def close(self):
        pass

class AndorSolisWorker(Worker):
    def init(self):
        if self.mock:
            print("Starting device worker as a mock device")
            self.cam = MockCamera()
        else:
            global AndorCam
            from .andor_sdk.andor_utils import AndorCam
            self.cam = AndorCam(self.name)

        print("Setting up acquisition...")
        self.setup_timed_acquisition(self.acq_attributes)
        self.setup_manual_acquisition(self.manual_mode_acq_attributes)
        print("Initialisation complete")

    def setup_timed_acquisition(self, attributes):
        # Stuff from andor_utils
        pass

    def setup_manual_acquisition(self, attributes):
        # Stuff from andor_utils
        pass


    def program_manual(self):
        if 'sensor_temperature' in worker_initialisation_kwargs.keys():
            cool_down = True
            temperature_setpoint = worker_initialisation_kwargs['sensor_temperature']
            print('Enabled sensor cooling...')
        else: 
            cool_down = False
            temperature_setpoint = 20
        
        if 'EMCCD_gain' in worker_initialisation_kwargs.keys():
            enable_EMCCD = True
            EMCCD_gain = worker_initialisation_kwargs['EMCCD_gain']
            print('Enabled EM sensor...')
        else:
            enable_EMCCD = False
            EMCCD_gain = self.cam.MIN_EG

        temp_set_timeout = 5

        self.cam.setup_sensor(cool_down, set_temp, temp_set_timeout, enable_EMCCD, EMCCD_gain)
        print(f'Current sensor temperature{self.cam.get_sensor_temp():.5f}')

    def transition_to_buffered(self):
        acquisition_mode = worker_initialisation_kwargs['acquisition_mode']

        if 'xbin' in worker_initialisation_kwargs.keys():
            xbin = worker_initialisation_kwargs['xbin']
            x0 = worker_initialisation_kwargs['x0']
            xf = worker_initialisation_kwargs['xf']
        else:
            xbin, x0, xf = 1, 1, self.cam.XPIX

        if 'ybin' in worker_initialisation_kwargs.keys():
            ybin = worker_initialisation_kwargs['ybin']
            y0 = worker_initialisation_kwargs['y0']
            yf = worker_initialisation_kwargs['yf']
        else:
            ybin, y0, yf = 1, 1, self.cam.YPIX

        if 'n_series' in worker_initialisation_kwargs.keys():
            n_series = worker_initialisation_kwargs['n_series']


        self.cam.setup_acquisition(acquisition_mode, xbin, ybin, x0, xf, y0, yf, 
                                   n_series, FK_time, FK_bin_mode, offset)
        self.cam.setup_trigger(trigger_mode, trigger_edge)
        self.cam.setup_exposure(exposure_time, internal_shutter_mode, external_shutter_mode)
        self.cam.setup_readout(readout_mode)
        self.cam.start_acquisition()

    def transition_to_manual(self):
        self.data = self.cam.grab_acquisition()
        self.program_manual()

    def abort_transition_to_buffered(self):
        pass

    def abort_buffered(self):
        pass

    def shutdown(self):
        keep_cooler_on = worker_initialisation_kwargs['keep_cooler_on']
        self.cam.system_close(keep_cooler_on)
