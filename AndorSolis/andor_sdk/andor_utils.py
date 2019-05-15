import numpy as np 
import time
import matplotlib.pyplot as plt

from andor_solis import *

ms, us, ns = 1e-3, 1e-6, 1e-9

class AndorCam(object):
    
    def __init__(self, name='anonymous_cam'):
        self.name = name
        Initialize()
        self.ANDORCAPS = GetCapabilities()
        self.HEAD_NAME = GetHeadModel()
        self.XPIX, self.YPIX = GetDetector()
        self.DXPIX, self.DYPIX = GetPixelSize()
        self.HARDWARE_VER = GetHardwareVersion()
        self.SOFTWARE_VER = GetSoftwareVersion()
        self.MIN_T, self.MAX_T = GetTemperatureRange()
        self.MIN_EG, self.MAX_EG = GetEMGainRange()
        self.TEMPERATURE, self.TEMP_STATUS = GetTemperatureF()

    def check_capabilities(self):
        # TODO: Maybe wait for Python 3 enum
        pass

    def setup_sensor(self, cool_down=False, temp_setpoint=20, temp_timeout=10, 
                     enable_EM=False, EM_gain=120):
        self.on_logged_temps = []
        
        # When cooling down, assume water cooling, so fan is off 
        if cool_down:
            SetFanMode(2)
            SetTemperature(temp_setpoint)
            CoolerON()
            # Wait for temperature to be stable
            while 'TEMPERATURE_NOT_REACHED' in self.TEMP_STATUS:
                time.sleep(temp_timeout) 
                self.TEMPERATURE, self.TEMP_STATUS = GetTemperatureF()
                self.on_logged_temps.append(self.TEMPERATURE)
            while 'TEMPERATURE_STABILIZED' not in self.TEMP_STATUS:
                time.sleep(temp_timeout)
                self.TEMPERATURE, self.TEMP_STATUS = GetTemperatureF()
                self.on_logged_temps.append(self.TEMPERATURE)
        
        if enable_EM:
            # Set EMCCD gain
            SetEMCCDGain(EM_gain)
            self.EMCCD_GAIN = GetEMCCDGain()
        return self.on_logged_temps

    def _setup_ccd_shift(self, mode, option=0):
        """ By default, set to horizontal max speed and 
            vertical min speed """
    
        # Vertical
        if 'fast_kinetics' not in mode:
            self.VS_NUMBER, self.VS_SPEED = GetFastestRecommendedVSSpeed()
            SetVSSpeed(self.VS_NUMBER)
        else:
            self.VS_NUMBER = GetNumberFKVShiftSpeeds()
            self.VS_SPEED = GetFKVShiftSpeedF(self.VS_NUMBER - 1 - option)
            SetFKVShiftSpeed(self.VS_NUMBER - 1 - option)
    
        # Horizontal --> default to max
        intermediate_speed, self.HS_NUMBER, AD_NUMBER = 0, 0, 0
        for channel in range(GetNumberADChannels()):
            n_allowed_speeds = GetNumberHSSpeeds(channel, 0)
            for speed_index in range(n_allowed_speeds):
                speed = GetHSSpeed(channel, 0, speed_index)
                if speed > intermediate_speed:
                    intermediate_speed = H_speed
                    self.HS_NUMBER = speed_index
                    AD_NUMBER = channel
        self.HS_SPEED = intermediate_speed
        SetADChannel(AD_NUMBER)
        SetHSSpeed(0, self.HS_NUMBER)

    def setup_acquisition(self, acquisition_mode='single', 
                          xbin=1, ybin=1, x0=1, xf=1024, y0=1, yf=1024, 
                          n_series=4, FK_time=20*ms, FK_binning_mode='full_image', offset=0):
        self.ACQ_MODE = acquisition_mode
    
        # Setup acquisition mode
        modes = {'single':1, 'accumulate':2, 'kinetics':3, 
                 'fast_kinetics':4, 'run_till_abort':5}
        SetAcquisitionMode(modes[acquisition_mode])
        
        # Setup pixel shifting speeds
        self._setup_ccd_shift(mode=acquisition_mode)
        
        # Setup image binning
        SetImage(xbin, ybin, x0, xf, y0, yf)
        

    def setup_readout(self, readout_mode='full_image', readout_shape=None):
        # Setup readout mode
        modes = {'FVB':0, 'multi-track':1, 'random-track':2, 
                 'single-track':3, 'full_image':4}
        SetReadMode(modes[readout_mode])
    
        if 'FVB' in readout_mode:
            self.DATA_SHAPE = (self.XPIX, 1)
        else: 
            self.DATA_SHAPE = (self.XPIX, self.YPIX)
    
        # Last chance to override data shape
        if readout_shape is not None:
            self.DATA_SHAPE = readout_shape
    
        if 'fast_kinetics' in self.ACQ_MODE:
            binning_modes = {'FBV':0, 'full_image':4}
    
            # Assume that full series fills CCD maximally, compute 
            # number of exposed rows per exposure in the series
            exposed_rows = int(self.YPIX/n_series)
    
            # Use the same binning as the one used to configure Image
            SetFastKineticsEx(exposed_rows, n_series, FK_time, 
                              binning_modes[FK_binning_mode], xbin, ybin, offset)
            self.EXPOSURE = GetFKExposureTime()
        else:
            self.EXPOSURE, self.ACCUMULATIONS, self.KINETICS = GetAcquisitionTimings()
    
        # Compute readout timing
        self.READOUT = GetReadOutTime() 

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
        
