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

from labscript_devices import labscript_device, BLACS_tab, BLACS_worker, runviewer_parser
from labscript import StaticAnalogQuantity, Device, LabscriptError, set_passed_properties
import numpy as np


@BLACS_worker
class NewFocusPicoMotorControllerWorker(Worker):
    def init(self):
        global socket; import socket
        global zprocess; import zprocess
        global h5py; import labscript_utils.h5_lock, h5py
        global time; import time

        self.port = 23
        self.prefix = '%s>' % self.slave

        # TODO change connectivity to establish connection only once
        # rather than every time I want to send a command

    def readline(self, socket):
        data = ''
        while True:
            char = socket.recv(1)
            data += char
            if char == '\n':
                return data


    def check_remote_values(self):
        # Get the currently output values:
        results = {}
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # time.sleep(0.1)
        assert self.port, 'No port number supplied.'
        assert self.host, 'No hostname supplied.'
        s.settimeout(5)
        s.connect((self.host, int(self.port)))

        for axis in range(1,5):
            command = self.prefix+"xxPA?"
            full_command = command.replace("xx", str(axis))
            # full_command = axis_command.replace("nn", str(value))
            # print full_command

            # retry 5 times to send the command
            for _ in range(5):
                try:
                    s.send(full_command +'\n')
                    # time.sleep(0.1)
                    # response = s.recv(1024)
                    response = self.readline(s)
                    # skip hex identifier in response
                    # print(self.host + ' init: ' + response)
                    # time.sleep(0.1)
                    results['%s'%axis] = int(response.split('>')[1].strip())
                    break
                except Exception as e:
                    print(e)
                    print('Retrying remote value check.')

        return results

    def check_connectivity(self, host):
        s = self.initialise_sockets(self.host, self.port)

        s.send(self.prefix+"*IDN?"+'\n')
        response = self.readline(s)

        # print response
        if '8742' in response:
            return s
        else:
            raise Exception('invalid response from host: ' + str(response))

    def initialise_sockets(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        assert port, 'No port number supplied.'
        assert host, 'No hostname supplied.'
        s.settimeout(5)
        s.connect((host, int(port)))
        # time.sleep(0.1)
        # s.send(self.prefix+"*IDN?"+'\n')
        # time.sleep(0.1)
        # response = s.recv(1024)
        # time.sleep(0.005)
        # s.close()
        return s

    def program_manual(self, front_panel_values):
        s = self.check_connectivity(self.host)
        # For each motor
        for axis in range(1,5):
            self.program_static(s, axis, int(front_panel_values["%s" %axis]))
            # time.sleep(0.01)

        s.close()
        # return {}
        return self.check_remote_values()


    def program_static(self, socket, axis, value):
        # Target Position ONLY
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # time.sleep(0.1)
        # assert self.port, 'No port number supplied.'
        # assert self.host, 'No hostname supplied.'
        # s.settimeout(5)
        # s.connect((self.host, int(self.port)))
        command = self.prefix+"xxPAnn"
        axis_command = command.replace("xx", str(axis))
        full_command = axis_command.replace("nn", str(value))
        # print full_command
        socket.send(full_command +'\n')
        # time.sleep(0.1)
        # s.recv(1024)  # clears buffer
        # time.sleep(0.005)
        # s.close()

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
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
        #self.program_manual(self.initial_values)
        return True

    def abort_buffered(self):
        return True

    def abort_transition_to_buffered(self):
        return True

    def shutdown(self):
        self.s.close()
