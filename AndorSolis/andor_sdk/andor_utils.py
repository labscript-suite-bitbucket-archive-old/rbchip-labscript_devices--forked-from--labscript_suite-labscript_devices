import numpy as np 
import time

from .andor_solis import *
from .andor_capabilities import *

s, ms, us, ns = 1.0, 1e-3, 1e-6, 1e-9

class AndorCam(object):
    
    def __init__(self, name='andornymous'):

        """ Methods of this class pack the sdk functions
        and define more convenient functions to carry out
        an acquisition """

        self.name = name
        self.cooling = False
        self.preamp = False
        self.emccd = False
        self.armed = False
        self.initialize_camera()
        
        self.default_acquisition_attrs = {
        'acquisition':'single',
        'emccd':False,
        'emccd_gain':120,
        'preamp':False,
        'preamp_gain':1.0,
        'exposure_time':20*ms,
        'shutter_output':'low',
        'int_shutter_mode':'auto',
        'ext_shutter_mode':'auto',
        'shutter_t_open':100,
        'shutter_t_close':100,
        'readout':'full_image',
        'trigger':'internal',
        'trigger_edge':'rising',
        'number_accumulations':1,
        'accumulation_period':3*ms,
        'number_kinetics':1,
        'kinetics_period':30*ms,
        'xbin':1,
        'ybin':1,
        'xlims':None,
        'ylims':None,
        'v_offset':0,
        'readout_shape':None,
        }

    def initialize_camera(self):
        """ Calls the initialization function and
        pulls several properties from the hardware side such 
        as information and capabilities, which are useful for
        future acquisition settings """
        print('Connecting to camera...')
        Initialize()
        
        # Pull model and other capabilities struct
        self.andor_capabilities = GetCapabilities()
        self.model = camera_type.get_type(self.andor_capabilities.ulCameraType)
        self.check_capabilities()

        # Pull hardware attributes
        self.head_name = GetHeadModel()
        self.x_size, self.y_size = GetDetector()
        self.x_pixel_size, self.y_pixel_size = GetPixelSize()
               
        self.hardware_version = GetHardwareVersion()

        # Pull software attributes
        self.software_version = GetSoftwareVersion()

        # Pull important capability ranges
        self.temperature_range = GetTemperatureRange()
        self.emccd_gain_range = GetEMGainRange()
        self.number_of_preamp_gains = GetNumberPreAmpGains()
        self.preamp_gain_range = (GetPreAmpGain(0), GetPreAmpGain(self.number_of_preamp_gains-1))

    def check_capabilities(self):
        """ Do checks based on the _AC dict """
        # Pull the hardware noted capabilities
        self.acq_caps = acq_mode.check(self.andor_capabilities.ulAcqModes)
        self.read_caps = read_mode.check(self.andor_capabilities.ulReadModes)
        self.trig_capability = trigger_mode.check(self.andor_capabilities.ulTriggerModes)
        self.pixmode = pixel_mode.check(self.andor_capabilities.ulPixelMode)
        self.setfuncs = set_functions.check(self.andor_capabilities.ulSetFunctions)
        self.getfuncs = get_functions.check(self.andor_capabilities.ulGetFunctions)
        self.features = features.check(self.andor_capabilities.ulFeatures)
        self.emgain_capability = em_gain.check(self.andor_capabilities.ulEMGainCapability)

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
        while 'TEMP_NOT_REACHED' in self.temperature_status:
            time.sleep(thermal_timeout)
            self.temperature, self.temperature_status = GetTemperatureF()
        while 'TEMP_STABILIZED' not in self.temperature_status:
            time.sleep(thermal_timeout)
            self.temperature, self.temperature_status = GetTemperatureF()

        self.cooling = True

        # Always return to ambient temperature on Shutdown
        SetCoolerMode(0)

    def enable_preamp(self, preamp_gain):
        """ Calls all the functions relative to the 
        preamplifier gain control. """

        if not preamp_gain in np.linspace(self.preamp_gain_range[0],
                                          self.preamp_gain_range[-1],
                                          self.number_of_preamp_gains):
            raise ValueError(f"Invalid preamp gain value..."+
                             f"valid range is {self.preamp_gain_range}")

        # Get all preamp options, match and set
        preamp_options = list([GetPreAmpGain(index) 
            for index in range(self.number_of_preamp_gains)])
        SetPreAmpGain(preamp_options.index(preamp_gain))
        self.preamp_gain = preamp_gain
        self.preamp = True

    def enable_emccd(self, emccd_gain):
        """ Calls all the functions relative to the 
        emccd gain control. """

        if not emccd_gain in self.emccd_gain_range:
            raise ValueError("Invalid emccd gain value, \
                             valid range is {self.emccd_gain_range}")

        if not self.cooling:
            raise ValueError("Please enable the temperature control before \
                enabling the EMCCD, this will prolong the lifetime of the sensor")

        SetEMCCDGain(emccd_gain)
        self.emccd_gain = GetEMCCDGain()
        self.emccd = True

    def setup_vertical_shift(self, custom_option=0):
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
                    intermediate_speed = speed
                    self.index_hs_speed = speed_index
                    ad_number = channel
        self.hs_speed = intermediate_speed
        SetADChannel(ad_number)
        SetHSSpeed(0, self.index_hs_speed)
     
    def setup_acquisition(self, added_attributes={}):
        """ Main acquisition configuration method. Available acquisition modes are
        below. The relevant methods are called with the corresponding acquisition 
        attributes dictionary, then the camera is armed and ready """
        # Override default acquisition attrs with added ones
        acquisition_attributes = self.default_acquisition_attrs
        for attr, val in added_attributes.items():
            acquisition_attributes[attr] = val
        
        self.acquisition_mode = acquisition_attributes['acquisition']

        if acquisition_attributes['preamp']:
            self.enable_preamp(acquisition_attributes['preamp_gain'])
        if acquisition_attributes['emccd']:
            self.enable_emccd(acquisition_attributes['emccd_gain'])

        # Available modes
        modes = {
        'single':1, 
        'accumulate':2, 
        'kinetic_series':3, 
        'fast_kinetics':4, 
        'run_till_abort':5,
        }

        SetAcquisitionMode(modes[self.acquisition_mode])

        # Set readout
        self.setup_readout(**acquisition_attributes)

        # Add acquisition specifications
        if 'accumulate' in self.acquisition_mode:
            self.configure_accumulate(**acquisition_attributes)
        elif 'kinetic_series' in self.acquisition_mode:
            self.configure_kinetic_series(**acquisition_attributes)
        elif 'fast_kinetics' in self.acquisition_mode:
            self.configure_fast_kinetics(**acquisition_attributes)
        elif 'run_till_abort' in self.acquisition_mode:
            self.configure_run_till_abort(**acquisition_attributes)

        # Configure shifting
        self.setup_vertical_shift()
        self.setup_horizontal_shift()

        # Setup shutter and trigger
        self.setup_shutter(**acquisition_attributes)
        self.setup_trigger(**acquisition_attributes)

        # Set exposure time, note that this may be overriden 
        # by the readout, trigger or shutter timings thereafter
        if 'exposure_time' in acquisition_attributes.keys():
            SetExposureTime(acquisition_attributes['exposure_time'])

        # Get actual timing information
        self.exposure_time, self.accum_timing, self.kinetics_timing = GetAcquisitionTimings()
    
        if 'fast_kinetics' in self.acquisition_mode:
            self.exposure_time = GetFKExposureTime()   

        # Set image (binning, cropping)
        self.setup_image(**acquisition_attributes)
        
        # Arm sensor
        self.armed = True
        
        self.readout_time = GetReadOutTime()
       
    def configure_accumulate(self, **attrs):
        """ Takes a sequence of single scans and adds them together """
        
        SetNumberAccumulations(attrs['number_accumulations'])
        
        # In External Trigger mode the delay between each scan making up 
        # the acquisition is not under the control of the Andor system but 
        # is synchronized to an externally generated trigger pulse.
        if 'internal' in attrs['trigger']:
            SetAccumulationCycleTime(attrs['accumulation_period'])


    def configure_kinetic_series(self, **attrs):
        """ Captures a sequence of single scans, or possibly, depending on 
        the camera, a sequence of accumulated scans """

        SetNumberKinetics(attrs['number_kinetics'])

        if 'internal' in attrs['trigger'] and attrs['number_kinetics'] > 1:
            SetKineticCycleTime(attrs['kinetics_period'])
                
        # Setup accumulations for the series if necessary
        if attrs['number_accumulations'] > 1:
            self.configure_accumulate(**attrs)

    def configure_fast_kinetics(self, **attrs):
        """ Special readout mode that uses the actual sensor as a temporary 
        storage medium and allows an extremely fast sequence of images to be 
        captured """

        fk_modes = {
        'FVB':0, 
        'full_image':4,
        }
    
        if 'exposed_rows' not in attrs.keys():
            # Assume that fast kinetics series fills CCD maximally, 
            # and compute the number of exposed rows per exposure 
            exposed_rows = int(self.y_size/attrs['number_kinetics'])
        else:
            exposed_rows = attrs['exposed_rows']

        SetFastKineticsEx(
            exposed_rows,
            attrs['number_kinetics'], 
            attrs['exposure_time'],
            fk_modes[attrs['readout']], 
            attrs['xbin'], 
            attrs['ybin'], 
            attrs['v_offset'],
        )

    def configure_run_till_abort(self, **attrs):
        """ Continually performs scans of the CCD until aborted """
        if 'internal' in attrs['trigger']: 
            SetKineticCycleTime(0)
        else:
            raise Exception("Can't run_till_abort mode if external trigger")

    def setup_trigger(self, **attrs):
        """ Sets different aspects of the trigger"""

        # Available modes
        modes = {
        'internal':0, 
        'external':1, 
        'external_start':6,
        }

        edge_modes = {
        'rising':0, 
        'falling':1,
        }

        SetTriggerMode(modes[attrs['trigger']])

        # Specify edge if external trigger
        if 'external' in attrs['trigger']:
            SetTriggerInvert(edge_modes[attrs['trigger_edge']])

    def setup_shutter(self, **attrs):
        """ Sets different aspects of the shutter and exposure"""
        
        # Available modes
        modes = {
        'auto':0, 
        'perm_open':1, 
        'perm_closed':2, 
        'open_FVB_series':4, 
        'open_any_series':5,
        }

        shutter_outputs = {
        'low':0, 
        'high':1,
        }

        SetShutter(
            shutter_outputs[attrs['shutter_output']], 
            modes[attrs['int_shutter_mode']], 
            attrs['shutter_t_close']+int(round(attrs['exposure_time']/ms)), 
            attrs['shutter_t_open'], 
        )

    def setup_readout(self, **attrs):
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

        SetReadMode(modes[attrs['readout']])
    
        # For full vertical binning setup a 1d-array shape
        if 'FVB' in attrs['readout']:
            self.image_shape = (int(1), int(self.x_size), int(1))
        else:
            self.image_shape = (int(attrs['number_kinetics']), 
                                int(self.x_size), int(self.y_size))
    
        # Last chance to override image shape
        if attrs['readout_shape'] is not None:
            self.image_shape = attrs['readout_shape']

    def setup_image(self, **attrs):
        """ Setup the binning attributes and the image attrs"""
        
        if attrs['xlims'] is None:
            attrs['xlims'] = (1, self.x_size)
        if attrs['ylims'] is None:
            attrs['ylims'] = (1, self.y_size)

        SetImage(
            attrs['xbin'], 
            attrs['ybin'], 
            *attrs['xlims'],
            *attrs['ylims'],
        )

    def snap(self, acquisition_timeout=5/ms):
        """ Carries down the acquisition, if the camera is armed and
        waits for an acquisition event for acquisition timeout (has to be
        in milliseconds), default to 5 seconds """
        
        def homemade_wait_for_acquisition():
            self.acquisition_status = GetStatus()
            start_wait = time.time()
            while 'DRV_IDLE' not in self.acquisition_status:
                self.acquisition_status = GetStatus()
                t0 = time.time() - start_wait
                if t0 > acquisition_timeout*ms:
                    break
                time.sleep(0.05)
                                                                
        if not self.armed:
            raise Exception("Cannot start acquisition until armed")
        else:
            self.acquisition_status = GetStatus()
            if 'DRV_IDLE' in self.acquisition_status:
                StartAcquisition()
                homemade_wait_for_acquisition()
                #WaitForAcquisitionTimeOut(int(round(acquisition_timeout)))
                #WaitForAcquisition()
            
            # Last chance, check if the acquisition is finished, update 
            # acquisition status and check for acquired data (if any),
            # otherwise, abort and raise an error
            self.acquisition_status = GetStatus()
            if 'DRV_IDLE' in self.acquisition_status:
                self.armed = False
                self.available_images = GetNumberAvailableImages()
            else:
                self.armed = False
                AbortAcquisition()
                raise AndorException('Acquisition aborted due to timeout')


    def grab_acquisition(self):
        """ Download buffered acquisition """
        return GetAcquiredData(self.image_shape).reshape(self.image_shape)

    def shutdown(self):
        """ Shuts camera down, if unarmed """
        if self.armed:
            raise ValueError("Cannot shutdown while the camera is armed, " +
                "please finish or abort the current acquisition before shutdown")
        else:
            ShutDown()
        
if __name__ in '__main__':
    
    cam = AndorCam()

    # First test should arm with default attrs and go
    cam.setup_acquisition(added_attributes={'exposure_time':25*ms,})
    cam.snap()
    single_acq_image = cam.grab_acquisition()
#    
#    # Second test, 3-shot kinetic series, internal trigger,
#    # similar to absorption imaging series
    internal_kinetics_attrs = {
    'exposure_time':20*ms,
    'acquisition':'kinetic_series',
    'number_kinetics':3,
    'kinetics_period':20*ms,
    'readout':'full_image',
    'int_shutter_mode':'perm_open',
    }
    cam.setup_acquisition(internal_kinetics_attrs)
    cam.snap()
    kinetics_series_images = cam.grab_acquisition()
    
    
    # Third test, 10-shot fast kinetics, internal trigger and no binning.
    fast_kinetics_attrs = {
    'exposure_time':1*ms,
    'acquisition':'fast_kinetics',
    'number_kinetics':16,
    'readout_shape':(1, cam.x_size, cam.y_size),
    'readout':'full_image',
    'int_shutter_mode':'perm_open',
    }
    cam.setup_acquisition(fast_kinetics_attrs)
    cam.snap()
    fast_kinetics_image = cam.grab_acquisition()
    
    import matplotlib.pyplot as plt
    plt.figure()
    plt.imshow(single_acq_image[0], cmap='seismic')
    
    plt.figure()
    ax = plt.subplot(311)
    ax.imshow(kinetics_series_images[0], cmap='seismic')
    ax = plt.subplot(312)
    ax.imshow(kinetics_series_images[1], cmap='seismic')
    ax = plt.subplot(313)
    ax.imshow(kinetics_series_images[2], cmap='seismic')
    
    plt.figure()
    plt.imshow(fast_kinetics_image[0], cmap='seismic')
    
    