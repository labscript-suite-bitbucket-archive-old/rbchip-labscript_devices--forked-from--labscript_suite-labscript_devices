#####################################################################
#                                                                   #
# /labscript_devices/AndorSolis/labscript_devices.py                #
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
import labscript_utils.h5_lock
import h5py

if PY2:
    str = unicode

__version__ = '1.0.0'

check_version('labscript', '2.5.0', '3.0.0')

from labscript import TriggerableDevice, LabscriptError, set_passed_properties

class AndorSolis(TriggerableDevice):
    description = "Andor scientific camera labscript driver"

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "model",
                "serial_number",
                "orientation",
                "manual_mode_acq_attributes",
                "mock",
            ],
            "device_properties": [
                "acq_attributes"
            ],
        } 
    )

    def __init__(
        self,  
        name, 
        parent_device,
        connection,
        model,
        serial_number,
        orientation='top',
        trigger_edge_type='falling',
        trigger_duration=None,
        minimum_recovery_time=0,
        acq_attributes=None,
        manual_mode_acq_attributes=None,
        mock=False,
        **kwargs
    ):
        self.model = model
        self.trigger_edge_type = trigger_edge_type
        self.minimum_recovery_time = minimum_recovery_time
        self.trigger_duration = trigger_duration
        self.orientation = orientation
        if isinstance(serial_number, (str, bytes)):
            serial_number = int(serial_number, 16)
        self.serial_number = serial_number
        self.BLACS_connection = hex(self.serial_number)[2:].upper()
        self.mock = mock
        if acq_attributes is None:
            acq_attributes = {}
        if manual_mode_acq_attributes is None:
            manual_mode_acq_attributes = {}
        self.acq_attributes = acq_attributes
        self.manual_mode_acq_attributes = manual_mode_acq_attributes
        self.exposures = []
        TriggerableDevice.__init__(self, name, parent_device, connection, **kwargs)

    def expose(self, t, name, frametype='frame', trigger_duration=None):
        if trigger_duration is None:
            trigger_duration = self.trigger_duration
        if trigger_duration is None:
            msg = """%s %s has not had an trigger_duration set as an instantiation
                argument, and none was specified for this exposure"""
            raise ValueError(dedent(msg) % (self.description, self.name))
        if not trigger_duration > 0:
            msg = "trigger_duration must be > 0, not %s" % str(trigger_duration)
            raise ValueError(msg)
        self.trigger(t, trigger_duration)
        self.exposures.append((t, name, frametype, trigger_duration))
        return trigger_duration

    def generate_code(self, hdf5_file):
        self.do_checks()
        vlenstr = h5py.special_dtype(vlen=str)
        table_dtypes = [
            ('t', float),
            ('name', vlenstr),
            ('frametype', vlenstr),
            ('trigger_duration', float),
        ]
        data = np.array(self.exposures, dtype=table_dtypes)
        group = self.init_device_group(hdf5_file)
        if self.exposures:
            group.create_dataset('EXPOSURES', data=data)
