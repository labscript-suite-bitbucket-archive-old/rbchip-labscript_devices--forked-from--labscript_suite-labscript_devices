#####################################################################
#                                                                   #
# /labscript_devices/AndorSolis/blacs_tabs.py                       #
#                                                                   #
# Copyright 2019, Joint Quantum Institute                           #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from __future__ import unicode_literals, division, absolute_import, print_function
from labscript_utils import PY2
import labscript_utils.h5_lock
import h5py

if PY2:
    str = unicode

import os

from qtutils import UiLoader, inmain_later
import qtutils.icons
from qtutils.qt import QtWidgets, QtGui, QtCore
import pyqtgraph as pg

from labscript_devices import BLACS_tab

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED 
from blacs.device_base_class import DeviceTab

import labscript_utils.properties

class AndorSolisTab(DeviceTab):
    def initialise_GUI(self):
        layout = self.get_tab_layout()
        ui_filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'andor_camera.ui'
            )
        self.ui = UiLoader().load(ui_filepath)

        self.ui.pushButton_acqconfig.clicked.connect(self.on_acqconfig_clicked)
        self.ui.pushButton_snap.clicked.connect(self.on_snap_clicked)
        self.ui.pushButton_cooldown.clicked.connect(self.on_cooldown_clicked)

        layout.addWidget(self.ui)
        self.image = pg.ImageView()
        self.image.setSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        self.ui.horizontalLayout.addWidget(self.image)

    def on_acqconfig_clicked(self, button):
        pass

    def on_snap_clicked(self, button):
        pass

    def on_cooldown_clicked(self, button):
        pass

    def initialise_workers(self):
        table = self.settings['connection_table']
        connection_table_properties = table.find_by_name(self.device_name).properties
        # The device properties can vary on a shot-by-shot basis, but at startup we will
        # initially set the values that are configured in the connection table, so they
        # can be used for manual mode acquisition:
        with h5py.File(table.filepath, 'r') as f:
            device_properties = labscript_utils.properties.get(
                f, self.device_name, "device_properties"
            )
        worker_initialisation_kwargs = {
            'model': connection_table_properties['model'],
            'serial_number': connection_table_properties['serial_number'],
            'orientation': connection_table_properties['orientation'],
            'acq_attributes': device_properties['acq_attributes'],
            'manual_mode_acq_attributes': connection_table_properties[
                'manual_mode_acq_attributes'
            ],
            'mock': connection_table_properties['mock'],
        }

        self.create_worker('main_worker', 
            "labscript_devices.AndorSolis.blacs_workers.AndorSolisWorker",
            worker_initialisation_kwargs)
        self.primary_worker = "main_worker"
