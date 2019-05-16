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
        self.armed = False

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

    def enable_emccdgain(self, emccd_gain=120):
        """ Calls all the functions relative to the 
        emccd gain control. """

        if not emccd_gain in self.emccd_gain_range:
            raise ValueError("Invalid emccd gain value")

        # Set 
        SetEMCCDGain(emccd_gain)
        self.emccd_gain = GetEMCCDGain()

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
            # This one means the acquisition expects at least than one 
            # exposure to be configured
            try:
                self.n_exposures = self.kwargs['n_exposures']
                self.series_time = self.kwargs['series_time']
                self.xbin = self.kwargs['xbin']
                self.ybin = self.kwargs['ybin']
                self.y_offset = self.kwargs['v_offset']
            except KeyError:
                self.n_exposures = 1
                self.series_time = 20*ms
                self.xbin = 1
                self.ybin = 1
                self.y_offset = 0
        try:    
            self.readout_mode = self.kwargs['readout_mode']
        except KeyError:
            self.readout_mode = 'full_image'

        # Configure shifting and readout
        self.setup_vertical_shift()
        self.setup_horizontal_shift()
        self.setup_readout()

        # Setup shutter and trigger
        

        # Arm sensor
        self.armed = True               

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
    
        # Setup image for fast kinetics mode
        if 'fast_kinetics' in self.acquisition_mode:
            modes = {'FVB':0, 'full_image':4}
    
            # Assume that fast kinetics series fills CCD maximally, 
            # and compute the number of exposed rows per exposure 
            exposed_rows = int(self.YPIX/n_series)
    
            # Use the same binning as the one used to configure Image
            SetFastKineticsEx(exposed_rows,
                self.n_exposures, 
                self.series_time,
                modes[self.readout_mode], 
                self.xbin, 
                self.ybin, 
                self.y_offset)
            self.exposure_time = GetFKExposureTime()
        else:
            self.exposure_time, self.accumulations, self.kinetics = GetAcquisitionTimings()
    
        # Compute readout timing
        self.readout_time = GetReadOutTime() 

    def setup_trigger(self, trigger_mode='external', trigger_edge_type='rising'):
        # Setup triggering
        modes = {'internal':0, 'external':1, 'external_start':6}
        edge_modes = {'rising':0, 'falling':1}
        SetTriggerMode(modes[trigger_mode])
        if trigger_mode is not 'internal':
            SetTriggerInvert(edge_modes[trigger_edge_type])
        

    def setup_exposure(self, exposure_time=1*ms, internal_shutter_mode='auto', 
                       shutter_output_ttl='low', t_open=0, t_close=0, 
                       external_shutter_mode='perm_open'):
        # Setup exposure
        shutter_modes = {'auto':0, 'perm_open':1, 'perm_closed':2, 
                         'open_FBV_series':4, 'open_any_series':5}
        shutter_output_ttl_levels = {'low':0, 'high':1}
        SetShutterEx(shutter_output_ttl_levels[shutter_output_ttl], shutter_modes[internal_shutter_mode], 
                     t_close, t_open, shutter_modes[external_shutter_mode])
        SetExposureTime(exposure_time)

    def start_acquisition(self):
        self.ACQ_STATUS = GetStatus()        
        if 'DRV_IDLE' in self.ACQ_STATUS:
            StartAcquisition()
            WaitForAcquisition()
        
        self.ACQ_STATUS = GetStatus()
        # TODO: Verify sensor is happy after acquisition is done?
        self.FIRST, self.LAST = GetNumberAvailableImages()

    def grab_acquisition(self):
        return GetAcquiredData(self.DATA_SHAPE)

    def system_close(self, keep_cooler_on=False, temp_timeout=10):
        # Read temperature, temperature status
        self.TEMPERATURE, self.TEMP_STATUS = GetTemperatureF()
        
        # Always return to ambient temperature on Shutdown
        SetCoolerMode(int(keep_cooler_on))
        
        # Manual cooler off
        # CoolerOFF()
        
        # Shutdown
        ShutDown()
        
    def get_sensor_temp(self):
        return GetTemperatureF()
        
