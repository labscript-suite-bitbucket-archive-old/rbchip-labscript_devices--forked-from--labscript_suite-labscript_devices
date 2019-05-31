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
from blacs.device_base_class import DeviceTab

from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED

class NewFocusPicomotor8742Tab(DeviceTab):
    def initialise_GUI(self):
        # Capabilities
        self.base_units = 'steps'
        self.base_min = -2147483648
        self.base_step = 10
        self.base_decimals = 0

        self.device = self.settings['connection_table'].find_by_name(self.device_name)
        self.num_motors = len(self.device.child_list)

        # Create the AO output objects
        ao_prop = {}
        for child_name in self.device.child_list:
            motor_type = self.device.child_list[child_name].device_class
            connection = self.device.child_list[child_name].parent_port
            if motor_type == 'Picomotor':
                base_max = 2147483647
            else:
                base_max = 2147483647

            ao_prop[connection] = {'base_unit':self.base_units,
                                   'min':self.base_min,
                                   'max':base_max,
                                   'step':self.base_step,
                                   'decimals':self.base_decimals
                                  }

        # Create the output objects
        self.create_analog_outputs(ao_prop)
        # Create widgets for output objects
        _, ao_widgets, _ = self.auto_create_widgets()
        # and auto place the widgets in the UI
        self.auto_place_widgets(("Position", ao_widgets))

        # Store the address
        self.blacs_connection = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)
        self.host, self.port = self.blacs_connection.split(',')

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(False)

    def initialise_workers(self):
        # Create and set the primary worker
        self.create_worker(
            'main_worker', 
            'labscript_devices.NewFocusPicomotor8742.blacs_workers.NewFocusPicomotor8742Worker', 
            {'host':self.host, 'port':self.port})
        self.primary_worker = 'main_worker'
