#####################################################################
#                                                                   #
# labscript_devices/NewFocusPicomotor8742.py                        #
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
import labscript_utils.properties

class NewFocusPicomotor8742Worker(Worker):
    def init(self):
        global h5py; import labscript_utils.h5_lock, h5py
        global PicoMotor8742Controller
        from .PicoMotor8742Controller import PicoMotor8742Controller
        self.dev = PicoMotor8742Controller(self.host, self.port, timeout=1)

        # Establish connectivity
        print('Connected to: ' + str(self.dev.identity()))

    def check_remote_values(self):
        remote_vals = dict({ax:self.dev.query_axis_abs(int(ax)) for ax in list(range(1, 5))})
        return remote_vals

    def program_manual(self, front_panel_values):
        # For each motor
        for axis in range(1,5):
            self.program_static(axis, int(front_panel_values["%s" %axis]))
        return self.check_remote_values()

    def program_static(self, axis, position):
        # Absolute positions ONLY
        self.dev.move_axis_abs(axis, position)

    def transition_to_buffered(self, device_name, h5file, initial_values, fresh):
        return_data = {}
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            if 'static_values' in group:
                data = group['static_values'][:][0]
        
        self.program_manual(data)
        for motor in data.dtype.names:
            return_data[motor] = data[motor]

        return return_data

    def transition_to_manual(self):
        pass

    def abort_buffered(self):
        pass

    def abort_transition_to_buffered(self):
        self.dev.abort_motion()

    def shutdown(self):
        pass
