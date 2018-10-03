from labscript_devices.NI_DAQmx.labscript_devices import NI_PCIe_6363
from labscript_devices.PulseBlasterUSB import PulseBlasterUSB

from labscript import (
    ClockLine,
    start,
    stop,
    labscript_init,
    AnalogOut,
    DigitalOut,
    StaticAnalogOut,
    StaticDigitalOut,
)

import sys
sys.excepthook = sys.__excepthook__

labscript_init('test.h5', new=True, overwrite=True)
PulseBlasterUSB('pulseblaster')
ClockLine('clock', pulseblaster.pseudoclock, 'flag 0')
NI_PCIe_6363(
    'Dev1',
    clock,
    model='PCIe-6363',
    clock_terminal='PFI0',
)

AnalogOut('ao0', Dev1, 'ao0')
AnalogOut('ao1', Dev1, 'ao1')

DigitalOut('do0', Dev1, 'port0/line0')
DigitalOut('do1', Dev1, 'port0/line1')

start()
t = 0
ao0.constant(t, 1)
t += 1
t += ao0.ramp(t, duration=1, initial=1, final=2, samplerate=10)
do1.go_high(t)
stop(t+1)
import os
os.system('hdfview test.h5 > /dev/null')