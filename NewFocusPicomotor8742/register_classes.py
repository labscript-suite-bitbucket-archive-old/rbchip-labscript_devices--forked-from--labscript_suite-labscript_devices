#####################################################################
#                                                                   #
# /labscript_devices/IMAQdxCamera/register_classes.py               #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'NewFocusPicomotor8742',
    BLACS_tab='labscript_devices.NewFocusPicomotor8742.blacs_tabs.NewFocusPicomotor8742Tab',
    runviewer_parser=None,
)
