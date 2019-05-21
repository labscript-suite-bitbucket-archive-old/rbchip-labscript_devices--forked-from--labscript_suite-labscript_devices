import numpy as np 
import time
import matplotlib.pyplot as plt

from andor_solis import *

s, ms, us, ns = 1.0, 1e-3, 1e-6, 1e-9

class AndorCam(object):
    
    def __init__(self, name='andornymous', model=None):

        """ Methods of this class packed the wrapped driver
        methods in andor_solis to define convenience functions"""

        self.name = name
        self.model = model
        self.initialize_camera()
        self.check_capabilities()
        self.cooling = False
        self.preamp = False
        self.emccd = False
        self.armed = False

    def initialize_camera(self):
        """ This method calls the initialization function and
        pulls several properties from the hardware side such 
        as information and capabilities, which are useful for
        future acquisition settings """
        Initialize()
        
        # Pull capabilities struct (as dict)
        self.andor_capabilities = GetCapabilities()

        # Pull hardware attributes
        self.head_name = GetHeadModel()
        self.x_size, self.y_size = GetDetector()
        self.x_pixel_size, self.y_pixel_size = GetPixelSize()
        self.hardware_version = GetHardwareVersion()

        # Pull software attributes
        self.software_version = GetSoftwareVersion()

        # Pull important capabilities ranges
        self.temperature_range = GetTemperatureRange()
        self.emccd_gain_range = GetEMGainRange()
        self.preamp_gain_range = list([GetPreAmpGain(gain_index) for 
            gain_index in range(GetNumberPreAmpGains())])

    def check_capabilities(self):
        # TODO: Here we do checks based on the _AC dict,
        # maybe wait for Python 3 enum
        pass

    def enable_cooldown(self, temperature_setpoint=20):
        """ Calls all the functions relative to temperature control
        and stabilization. Enables cooling down, waits for stabilization
        and finishes when the status first gets a stabilized setpoint """

        if not temperature_setpoint in self.temperature_range:
            raise ValueError("Invalid temperature setpoint")

        # Set the thermal timeout to several seconds (realistic 
        # thermalization will happen over this timescale)
        thermal_timeout = 10*s

        # Pull latest temperature and temperature status
        self.temperature, self.temperature_status = GetTemperatureF()

        # When cooling down, assume water cooling is present, 
        # so the fan has to be set to off 
        SetFanMode(2)

        # Set temperature and enable TEC
        SetTemperature(temperature_setpoint)
        CoolerON()

        # Wait until stable
        while 'TEMPERATURE_NOT_REACHED' in self.temperature_status:
            time.sleep(thermal_timeout)
            self.temperature, self.temperature_status = GetTemperatureF()
        while 'TEMPERATURE_STABILIZED' not in self.temperature_status:
            time.sleep(thermal_timeout)
            self.temperature, selt.temperature_status = GetTemperatureF()

        self.cooling = True

        # Always return to ambient temperature on Shutdown
        SetCoolerMode(0)

    def enable_preampgain(self, preamp_gain=1):
        """ Calls all the functions relative to the 
        preamplifier gain control. """

        if not preamp_gain in self.preamp_gain_range:
            raise ValueError("Invalid preamp gain value")

        # Get all preamp options, match and set
        index_preamp_gains = list(range(GetNumberPreAmpGains()))
        preamps_options = list([GetPreAmpGain(index) for index in index_preamp_gains])
        SetPreAmpGain(preamps_options.index(preamp_gain))
        self.preamp_gain = preamp_gain
        self.preamp = True

    def enable_emccdgain(self, emccd_gain=120):
        """ Calls all the functions relative to the 
        emccd gain control. """

        if not emccd_gain in self.emccd_gain_range:
            raise ValueError("Invalid emccd gain value")

        if not self.cooling:
            raise ValueError("Please enable the temperature control before \
                enabling the EMCCD, this will prolong the lifetime of the sensor")

        SetEMCCDGain(emccd_gain)
        self.emccd_gain = GetEMCCDGain()
        self.emccd = True

    def setup_vertical_shift(self, custom_option=None):
        """ Calls the functions needed to adjust the vertical
        shifting speed on the sensor for a given acquisition"""

        # Sets to the slowest one by default to mitigate noise
        # unless the acquisition has been explicitly chosen
        # to be in fast kinetics mode, for which custom methods 
        # are used and a custom_option shifts between available
        # speeds
        if 'fast_kinetics' not in self.acquisition_mode:
            self.index_vs_speed, self.vs_speed = GetFastestRecommendedVSSpeed()
            SetVSSpeed(self.index_vs_speed)
        else:
            self.number_fkvs_speeds = GetNumberFKVShiftSpeeds()
            if not custom_option in range(self.number_fkvs_speeds):
                raise ValueError("Invalid vertical shift speed custom option value")
            SetFKVShiftSpeed(custom_option)
            self.vs_speed = GetFKVShiftSpeedF(custom_option)

    def setup_horizontal_shift(self, custom_option=None):
        """ Calls the functions needed to adjust the horizontal
        shifting speed on the sensor for a given acquisition""" 

        # Sets to the fastest one by default to reduce download time
        # but this probably plays down on the readout noise
        intermediate_speed, self.index_hs_speed, ad_number = 0, 0, 0
        for channel in range(GetNumberADChannels()):
            n_allowed_speeds = GetNumberHSSpeeds(channel, 0)
            for speed_index in range(n_allowed_speeds):
                speed = GetHSSpeed(channel, 0, speed_index)
                if speed > intermediate_speed:
                    intermediate_speed = H_speed
                    self.index_hs_speed = speed_index
                    ad_number = channel
        self.hs_speed = intermediate_speed
        SetADChannel(ad_number)
        SetHSSpeed(0, self.index_hs_speed)
     
    def image_binning(self, xbin, ybin, xlims, ylims):
        """ Enable and setup the binning attributes, 
        xbin and ybin are the sizes, xlims and ylims are
        tuples with the binning limits """
        SetImage(xbin, ybin, *xlims, *ylims)

    def setup_acquisition(self, acquisition_mode='single', **kwargs):
        """ Main acquisition configuration method. Available acquisition modes are
        below, calls the relevant methods in the appropriate order, then the 
        camera is armed and ready for the *snap* call """

        self.acquisition_mode = acquisition_mode
        
        # Available modes
        modes = {
        'single':1, 
        'accumulate':2, 
        'kinetics':3, 
        'fast_kinetics':4, 
        'run_till_abort':5,
        }

        SetAcquisitionMode(modes[self.acquisition_mode])
        
        # Check for extra call arguments (e.g for series acquisition)
        if 'kinetics' in self.acquisition_mode:
            # This one means the acquisition expects at least one 
            # exposure to be configured
            try:
                self.n_exposures = kwargs['n_exposures']
                self.series_time = kwargs['series_time']
                self.xbin = kwargs['xbin']
                self.ybin = kwargs['ybin']
                self.y_offset = kwargs['v_offset']
            except KeyError:
                self.n_exposures = 2
                self.series_time = 20*ms
                self.xbin = 1
                self.ybin = 1
                self.y_offset = 0
        try:    
            self.readout_mode = kwargs['readout_mode']
            self.int_shutter_mode = kwargs['int_shutter_mode']
            self.ext_shutter_mode = kwargs['ext_shutter_mode']
            self.trigger_mode = kwargs['trigger_mode']
            self.trigger_edge = kwargs['trigger_edge']
            self.shutter_t_open = kwargs['shutter_t_open']
            self.shutter_t_close = kwargs['shutter_t_close']
        except KeyError:
            self.readout_mode = 'full_image'
            self.int_shutter_mode = 'auto'
            self.ext_shutter_mode = 'perm_open'
            self.shutter_t_close = 0
            self.shutter_t_open = 0
            self.trigger_mode = 'internal'
            self.trigger_edge = 'rising'

        # Setup shutter and trigger
        self.setup_trigger()
        self.setup_shutter()

        # Configure shifting and readout
        self.setup_vertical_shift()
        self.setup_horizontal_shift()
        self.setup_readout()

        # Arm sensor
        self.armed = True               

    def setup_trigger(self):
        """ Sets different aspects of the trigger"""

        # Available modes
        modes = {
        'internal':0, 
        'external':1, 
        'external_start':6,
        }

        edge_modes = {'rising':0, 'falling':1}
        SetTriggerMode(modes[self.trigger_mode])
        # Specify edge if external trigger 
        if self.trigger_mode is not 'internal':
            SetTriggerInvert(edge_modes[self.trigger_edge])

    def setup_shutter(self):
        """ Sets different aspects of the shutter and exposure"""
        
        # Available modes
        modes = {
        'auto':0, 
        'perm_open':1, 
        'perm_closed':2, 
        'open_FVB_series':4, 
        'open_any_series':5,
        }

        shutter_outputs = {'low':0, 'high':1}

        # Set shutter configuration
        SetShutterEx(
            shutter_outputs[self.shutter_output], 
            shutter_modes[self.int_shutter_mode], 
            self.shutter_t_close, 
            self.shutter_t_open, 
            shutter_modes[self.ext_shutter_mode],
        )

    def setup_readout(self, readout_shape=None):
        """ Sets different aspects of the data readout, including 
        image shape, readout mode """

        # Available modes
        modes = {
        'FVB':0, 
        'multi-track':1, 
        'random-track':2, 
        'single-track':3, 
        'full_image':4,
        }

        SetReadMode(modes[self.readout_mode])
    
        # For full vertical binning setup a 1d-array shape
        if 'FVB' in self.readout_mode:
            self.image_shape = (self.x_pixel_size, 1)
        else: 
            self.image_shape = (self.x_pixel_size, self.y_pixel_size)
    
        # Last chance to override image shape
        if self.readout_shape is not None:
            self.image_shape = readout_shape
    
        # Setup image for fast kinetics mode, compute timings
        if 'fast_kinetics' in self.acquisition_mode:
            fk_modes = {'FVB':0, 'full_image':4}
    
            # Assume that fast kinetics series fills CCD maximally, 
            # and compute the number of exposed rows per exposure 
            exposed_rows = int(self.y_size/self.n_exposures)
    
            # Use the same binning as the one used to configure Image
            SetFastKineticsEx(exposed_rows,
                self.n_exposures, 
                self.series_time,
                fk_modes[self.readout_mode], 
                self.xbin, 
                self.ybin, 
                self.y_offset)
            self.exposure_time = GetFKExposureTime()
        else:
            self.exposure_time, self.accumulations, self.kinetics = GetAcquisitionTimings()
    
        # Compute readout timing
        self.readout_time = GetReadOutTime() 

    def snap(self):
        """ Carries down the acquisition, if the camera is armed """
        if not self.armed:
            raise ValueError
        else:
            self.acquisition_status = GetStatus() 
            if 'DRV_IDLE' in self.acquisition_status:
                StartAcquisition()
                WaitForAcquisition()
        
            self.acquisition_status = GetStatus()
            self.number_available_images = GetNumberAvailableImages()

    def grab_acquisition(self):
        """ Download buffered acquisition, unarm sensor """

        # TODO: Check acquisition status, raise any exceptions

        data = GetAcquiredData(self.image_shape)
        self.armed = False
        return data.astype(int)

    def shutdown(self):
        """ Shuts camera down, if unarmed """
        if self.armed:
            raise ValueError("Cannot shutdown while the camera is armed, " +
                "please finish or abort the current acqusition before shutdown")
        elif self.emccd or self.preamp:
            # Default gains
            self.enable_preampgain(preamp_gain=1)
            self.enable_emccdgain(emccd_gain=120)
        else:    
            ShutDown()
        
if __name__ in '__main__':
    cam = AndorCam(name='brave_tester')

    # Global settings should be set at least once
    cam.enable_cooldown(temperature_setpoint=10)
    cam.enable_preampgain(preamp_gain=2)
    
    # First test, no specifications, should arm default and go
    cam.setup_acquisition()
    cam.snap()
    image = cam.grab_acquisition()

    # Second test, some specifications, should arm, wait for ext-trig and go
    cam.enable_emccdgain(emccd_gain=120)
    cam.setup_acquisition('kinetics', 
        n_exposures=3, 
        )