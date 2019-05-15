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
from labscript_utils import PY2, check_version
import numpy as np

if PY2:
    str = unicode

__version__ = '1.0.0'

check_version('labscript', '2.5.0', '3.0.0')

from labscript import StaticAnalogOut, Device, LabscriptError, set_passed_properties

class Picomotor(StaticAnalogOut):
    """ Single axis child class """
    min_pos = -2147483648
    max_pos = 2147483647
    description = 'Picomotor axis'

class NewFocusPicomotor8742(Device):
    description = "NewFocus 8742 controller labscript driver"
    allowed_children = [Picomotor]

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "host",
                "port",
                "serial_number",
            ],
        } 
    )

    def __init__(self, 
        name, 
        host="localhost", 
        port=23, 
        serial_number=1, 
        **kwargs
        ):

        self.name = name
        self.host = host
        self.port = port
        self.serial_number = serial_number
        Device.__init__(self, name, None, None, None)
        self.BLACS_connection = '%s,%d' %(host, port)

    def generate_code(self, hdf5_file):
        data_dict = {}
        for i, motor_axis in enumerate(self.child_devices):
            ignore = motor_axis.get_change_times()
            motor_axis.make_timeseries([])
            motor_axis.expand_timeseries()
            ax = motor_axis.connection
            value = motor_axis.raw_output[0]
            if not motor_axis.min_pos <= value <= motor_axis.max_pos:
                # Out of bounds position
                raise LabscriptError('%s %s has value out of bounds. \
                    Set value: %s Allowed range: %s to %s.'%(motor_axis.description,
                    motor_axis.name, str(value), 
                    motor_axis(motor_axis.min_pos),
                    str(motor_axis.max_pos)))
            if ax not in range(1, 5):
                # 8742 only supports 4 axes
                raise LabscriptError('%s %s has invalid connection number: %s'%(
                    motor_axis.description, motor_axis.name, 
                    str(motor_axis.connection)))
            data_dict[str(motor_axis.connection)] = value
        dtypes = [(conn, int) for conn in data_dict]
        data_array = np.zeros(1, dtype=dtypes)
        for conn in data_dict:
            data_array[0][conn] = data_dict[conn]
        grp = hdf5_file.create_group('/devices/' + self.name)
        grp.create_dataset('static_values', data=data_array)
