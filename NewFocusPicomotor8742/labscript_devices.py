#####################################################################
#                                                                   #
# labscript_devices/NewFocusPicoMotorController.py                  #
#                                                                   #
# Copyright 2016, Joint Quantum Institute                           #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2, check_version

if PY2:
    str = unicode

__version__ = '1.0.0'

check_version('labscript', '2.5.0', '3.0.0')

from labscript import StaticAnalogQuantity, Device, LabscriptError, set_passed_properties

#from PicoMotorController_8742 import NewFocus8742

class NewFocus8742Axis(StaticAnalogQuantity):
    """ Single axis child class """
    min_pos = -2147483648
    max_pos = 2147483647
    description = 'PicoMotorAxis'

class NewFocusPicoMotorController_8742(Device):
    description = "NewFocus 8742 controller driver"

    allowed_children = [NewFocus8742Axis]

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "host",
                "port",
                "serial_number",
            ],
            "device_properties": ["timeout"],
        } 
    )

    def __init__(self, 
        name, 
        host="localhost", 
        port=23, 
        serial_number=1, 
        **kwargs
    ):
    
    """ NewFocus Picomotor controller class """

        self.name = name
        self.host = host
        self.port = port
        self.serial_number = serial_number
        Device.__init__(self, name, None, None, None)
        self.BLACS_connection = '%s,%d' %(host, slave)


    def generate_code(self, hdf5_file):
        data_dict = {}
        for motor in self.child_devices:
            # Call these functions to finalise the motor, they are standard functions of all subclasses of Output:
            ignore = motor.get_change_times()
            motor.make_timeseries([])
            motor.expand_timeseries()
            connection = [int(s) for s in motor.connection.split() if s.isdigit()][0]
            value = motor.raw_output[0]
            if not motor.minval <= value <= motor.maxval:
                # error, out of bounds
                raise LabscriptError('%s %s has value out of bounds. Set value: %s Allowed range: %s to %s.'%(motor.description,motor.name,str(value),motor(motor.minval),str(motor.maxval)))
            if not connection > 0 and not connection < 5:
                # error, invalid connection number
                raise LabscriptError('%s %s has invalid connection number: %s'%(motor.description,motor.name,str(motor.connection)))
            data_dict[str(motor.connection)] = value
        dtypes = [(conn, int) for conn in data_dict]
        data_array = np.zeros(1, dtype=dtypes)
        for conn in data_dict:
            data_array[0][conn] = data_dict[conn]
        grp = hdf5_file.create_group('/devices/'+self.name)
        grp.create_dataset('static_values', data=data_array)
