import sys

import yaml
import cv2
import pygame
import numpy as np
from PIL import Image
from Camera.Camera import Camera
import Camera.amcam.amcam as amcam
import io
import time
from pathlib import Path

class AmscopeCamera(Camera):
    camera = None
    frame = None
    width = 0
    height = 0
    name = ""
    runtime = 0

    printerPosition = (0, 0, 0)
    isTakingImage = False

    buffer = []
    lastImage = None
    captureIndex = 1
    capturePath = "./output/"
    captureName = "test"

    _autoExposure = False
    _exposure = 120 # Optimal is 120
    _temp = 11616
    _tint = 925
    _level_range_low = (0, 0, 0, 0)
    _level_range_high = (255, 255, 255, 255)
    _contrast = 0
    _hue = 0
    _saturation = 126 # Optimal is 126
    _brightness = -64 # Optimal is -64
    _gamma = 100
    _wbgain = (0, 0, 0)
    _sharpening = 500 # Optimal is 500
    _linear = 0 # Optimal is 0
    _curve = 'Polynomial' # Optimal is Polynomial
    _image_file_format = 'png'

    def initialize(self):
        # Find Camera
        availableCameras = amcam.Amcam.EnumV2()
        if(len(availableCameras) <= 0):
            raise Exception("Failed to Find Amscope Camera")
        
        # Start the Camera
        self.name = availableCameras[0].displayname
        try:
            self.camera = amcam.Amcam.Open(availableCameras[0].id)
        except amcam.HRESULTException as e: print(e)
        else:
            self.width, self.height = self.camera.get_Size()
            self.buffer = bytes((self.width * 24 + 31) // 32 * 4) * self.height
            print(f"Number of still resolutions supported: {self.camera.StillResolutionNumber()}")
            try:
                if sys.platform == 'win32':
                    self.camera.put_Option(amcam.AMCAM_OPTION_BYTEORDER, 0) # QImage.Format_RGB888
                         
            except amcam.HRESULTException as e: print(e)
        self.startStream()

    def startStream(self):
        self.resetCameraSettings()
        self.loadCameraSettings()
        self.setCameraSettings()
        try:
            self.camera.StartPullModeWithCallback(self.cameraCallback, self)
            self.resize(self.width, self.height)
        except amcam.HRESULTException as e: print(e)
    
    @staticmethod
    def cameraCallback(event, _self: 'Camera'):
        if event == amcam.AMCAM_EVENT_STILLIMAGE:
            _self._processFrame()
            #_self.saveStillImage()
        elif event == amcam.AMCAM_EVENT_IMAGE:
            _self.stream()
        elif event == amcam.AMCAM_EVENT_EXPO_START:
            print("Please Open an issue on the github repo at https://github.com/AnthonyvW/tree-core/issues stating you found Expo Start along with the conditions in which this occured.")

    def resetCameraSettings(self):
        #   (From the API)
        #   .-[ DEFAULT VALUES FOR THE IMAGE ]--------------------------------.
        #   | Parameter                | Range         | Default              |
        #   |-----------------------------------------------------------------|
        #   | Auto Exposure Target     | 16~235        | 120                  |
        #   | Temp                     | 2000~15000    | 6503                 |
        #   | Tint                     | 200~2500      | 1000                 |
        #   | LevelRange               | 0~255         | Low = 0, High = 255  |
        #   | Contrast                 | -100~100      | 0                    |
        #   | Hue                      | -180~180      | 0                    |
        #   | Saturation               | 0~255         | 128                  |
        #   | Brightness               | -64~64        | 0                    |
        #   | Gamma                    | 20~180        | 100                  |
        #   | WBGain                   | -127~127      | 0                    |
        #   | Sharpening               | 0~500         | 0                    |
        #   | Linear Tone Mapping      | 1/0           | 1                    |
        #   | Curved Tone Mapping      | Log/Pol/Off   | 2 (Logarithmic)      |
        #   '-----------------------------------------------------------------'

        # Resets Camera Settings back to default values

        _autoExposure = False
        _exposure = 120 # Optimal is 120
        _temp = 11616
        _tint = 925
        _level_range_low = (0, 0, 0, 0)
        _level_range_high = (255, 255, 255, 255)
        _contrast = 0
        _hue = 0
        _saturation = 126 # Optimal is 126
        _brightness = -64 # Optimal is -64
        _gamma = 100
        _wbgain = (0, 0, 0)
        _sharpening = 500 # Optimal is 500
        _linear = 0 # Optimal is 0
        _curve = 'Polynomial' # Optimal is Polynomial
        _image_file_format = 'png'

    def loadCameraSettings(self):  # With code borrowed from https://stackoverflow.com/questions/1773805/how-can-i-parse-a-yaml-file-in-python
        try:
            with open("amscope_camera_configuration.yaml", "r") as stream:
                try:
                    settings = yaml.safe_load(stream)
                    self._autoExposure = settings['auto_expo']
                    self._exposure = settings['exposure']
                    self._temp = settings['temp']
                    self._tint = settings['tint']
                    self._level_range_low = settings['levelrange_low']
                    self._level_range_high = settings['levelrange_high']
                    self._contrast = settings['contrast']
                    self._hue = settings['hue']
                    self._saturation = settings['saturation']
                    self._brightness = settings['brightness']
                    self._gamma = settings['gamma']
                    self._wbgain = settings['wbgain']
                    self._sharpening = settings['sharpening']
                    self._linear = settings['linear']
                    self._curve = settings['curve']
                    self._image_file_format = settings['fformat']
                except yaml.YAMLError as e:
                    print('YAML ERROR >', e)
                except OSError as e:
                    print('OS ERROR >', e)
        except Exception as e:
            print('GENERAL ERROR >', e)

    def setCameraSettings(self, **kwargs): # With code taken from TRIM V1
        """
        @brief Modifies the microscope camera's image settings.

        @kwargs
         - auto_expo: Whether to enable the auto exposure (1/0).
         - exposure: The auto exposure target (16 ~ 235).
         - temp: The temperature value of the image (2000 ~ 15000).
         - tint: The tint of the image (200 ~ 2500).
         - levelrange_low: The low end of the level range
                           (0~255, 0~255, 0~255, 0~255).
         - levelrange_high: The high end of the level range
                            (0~255, 0~255, 0~255, 0~255).
         - contrast: The contrast value of the image (-100 ~ 100).
         - hue: The hue value of the image (-180 ~ 180).
         - saturation: The saturation value of the image (0 ~ 255).
         - brightness: The brightness value of the image (-64 ~ 64).
         - gamma: The gamma value of the image (20 ~ 180).
         - wbgain: The white balance rgb-triplet of the image
                   (-127~127, -127~127, -127~127).
         - sharpness: The amount of sharpness to use on the image (0~500).
         - linear: Whether to use linear (...) or not (1/0).
         - curve: Whether to use curve (...) or not (2/1/0).
         - fformat: The image file format to save as (png/jpg).

        """

        if 'auto_expo' in kwargs:
            self._autoExposure = int(kwargs.get('auto_expo', ''))
        if 'exposure' in kwargs:
            self._exposure = kwargs.get('exposure', '')
        if 'temp' in kwargs:
            self._temp = kwargs.get('temp', '')
        if 'tint' in kwargs:
            self._tint = kwargs.get('tint', '')
        if 'levelrange_low' in kwargs:
            self._level_range_low = (
                kwargs.get('levelrange_low', '')[0],
                kwargs.get('levelrange_low', '')[1],
                kwargs.get('levelrange_low', '')[2],
                kwargs.get('levelrange_low', '')[3]
            )
        if 'levelrange_high' in kwargs:
            self._level_range_high = (
                kwargs.get('levelrange_high', '')[0],
                kwargs.get('levelrange_high', '')[1],
                kwargs.get('levelrange_high', '')[2],
                kwargs.get('levelrange_high', '')[3]
            )
        if 'contrast' in kwargs:
            self._contrast = kwargs.get('contrast', '')
        if 'hue' in kwargs:
            self._hue = kwargs.get('hue', '')
        if 'saturation' in kwargs: 
            self._saturation = kwargs.get('saturation', '')
        if 'brightness' in kwargs:
            self._brightness = kwargs.get('brightness', '')
        if 'gamma' in kwargs:
            self._gamma = kwargs.get('gamma', '')
        if 'wbgain' in kwargs:
            self._wbgain = (
                kwargs.get('wbgain', '')[0],
                kwargs.get('wbgain', '')[1],
                kwargs.get('wbgain', '')[2]
            )
        if 'sharpening' in kwargs:
            self._sharpening = int(kwargs.get('sharpening', ''))
        if 'linear' in kwargs:
            self._linear = int(kwargs.get('linear', ''))
        if 'curve' in kwargs:
            self._curve = kwargs.get('curve', '')
        if 'fformat' in kwargs:
            self._image_file_format = kwargs.get('fformat', '')

        if kwargs: print(kwargs)
        try:
            if self._autoExposure is not None: self.camera.put_AutoExpoEnable(self._autoExposure)
            if self._exposure is not None: self.camera.put_AutoExpoTarget(self._exposure)
            if self._temp is not None and\
                self._tint is not None: self.camera.put_TempTint(self._temp, self._tint)
            if self._level_range_high is not None and\
                self._level_range_low is not None: self.camera.put_LevelRange(self._level_range_low, self._level_range_high)
            if self._contrast is not None: self.camera.put_Contrast(self._contrast)
            if self._hue is not None: self.camera.put_Hue(self._hue)
            if self._saturation is not None: self.camera.put_Saturation(self._saturation)
            if self._brightness is not None: self.camera.put_Brightness(self._brightness)
            if self._gamma is not None: self.camera.put_Gamma(self._gamma)
            if self._sharpening is not None: self.camera.put_Option(amcam.AMCAM_OPTION_SHARPENING, self._sharpening)
            if self._linear is not None: self.camera.put_Option(amcam.AMCAM_OPTION_LINEAR, self._linear)
            if self._curve is not None:
                if self._curve == 'Off': self.camera.put_Option(amcam.AMCAM_OPTION_CURVE, 0)
                if self._curve == 'Polynomial': self.camera.put_Option(amcam.AMCAM_OPTION_CURVE, 1)
                if self._curve == 'Logarithmic': self.camera.put_Option(amcam.AMCAM_OPTION_CURVE, 2)
            #if self._wbgain is not None: self.camera.put_WhiteBalanceGain(self._wbgain) ! Not implemented yet
        except amcam.HRESULTException as e:
            print(e)
        except AttributeError as e:
            print(e)

    def getCameraSettings(self):
        return (
            self._autoExposure,
            self._exposure,
            self._temp,
            self._tint,
            self._contrast,
            self._hue,
            self._saturation,
            self._brightness,
            self._sharpening,
            self._linear,
            self._curve,
            self._image_file_format,
        )

    def resize(self, frameWidth, frameHeight):
        if(self.frame != None):
            self.scale = min(frameWidth/self.frame.get_width(), frameHeight/self.frame.get_height())

    def stream(self):
        try:
            self.camera.PullImageV2(self.buffer, 24, None)
        except amcam.HRESULTException as e: print(e)
        else:
            self.width, self.height = self.camera.get_Size()
            self.frame = pygame.image.frombuffer(self.buffer, [self.width, self.height], 'RGB')

    def getFrame(self):
        return pygame.transform.scale_by(self.frame, self.scale)

    def update(self):
        return self.frame

    def captureAndSaveImage(self, position):
        print("Taking Image", position[0])
        self.printerPosition = position[0]
        self.isTakingImage = True
        self.camera.Snap(0)
        self.saveImage()

    def captureImage(self, position):
        print("Capturing Image", position[0])
        self.printerPosition = position[0]
        self.isTakingImage = True
        self.camera.Snap(0)

    def _processFrame(self):
        self.isTakingImage = True
        camWidth = self.camera.get_StillResolution(0)[0]
        camHeight = self.camera.get_StillResolution(0)[1]
        buffer_size = camWidth * camHeight * 3
        buf = bytes(buffer_size)
        self.camera.PullStillImageV2(buf, 24, None)
        decoded = np.frombuffer(buf, np.uint8)
        decoded = decoded.reshape((camHeight, camWidth, 3))
        self.lastImage = decoded
        self.isTakingImage = False

    def saveImage(self, folder = ""):

        if(folder != ""):
            folder += "/"
        # Wait until camera is done taking image
        while(self.isTakingImage):
            time.sleep(0.01)  # Avoid excessive CPU usage

        try:
            
            Path(self.capturePath + folder).mkdir(parents=True, exist_ok=True)
            name = self.capturePath + folder + self.captureName + str(self.captureIndex) + "PX" + str(self.printerPosition[0]) + "Y" + str(self.printerPosition[1]) + "Z" + str(self.printerPosition[2]) + "." + self._image_file_format
            print("Saving Image:", name)
            img = Image.fromarray(self.lastImage)
            img.save(name)
            self.captureIndex += 1
        except amcam.HRESULTException as e: print(e)

    def isBlack(self):
        while(self.isTakingImage):
            time.sleep(0.01)  # Avoid excessive CPU usage
        # Calculate some basic statistics
        colors = ('r', 'g', 'b')
        stdDev = []
        for i, color in enumerate(colors):
            channel = self.lastImage[:,:,i]
            stdDev.append(float(np.std(channel)))
        
        if(stdDev[0] < 5 or stdDev[1] < 5 or stdDev[2] < 5):
            return True
        else:
            print("Standard Deviation :", stdDev)
            return False

    def calculate_quadrant_focus(self, image, kernel_size=5, threshold=100):
        """
        Calculate focus measures for each quadrant of the image.
        
        Args:
            image: numpy array of the image
            kernel_size (int): Size of the Laplacian kernel
            threshold (float): Threshold for determining if quadrant is in focus
            
        Returns:
            tuple: (quadrant_scores, best_score, best_quadrant, histogram_data)
        """
        height, width = image.shape[:2]
        mid_h, mid_w = height // 2, width // 2
        
        # Define quadrants
        quadrants = [
            ('Top Left', image[0:mid_h, 0:mid_w]),
            ('Top Right', image[0:mid_h, mid_w:]),
            ('Bottom Left', image[mid_h:, 0:mid_w]),
            ('Bottom Right', image[mid_h:, mid_w:])
        ]
        
        quadrant_scores = {}
        
        for name, quad in quadrants:
            # Convert quadrant to grayscale if it's not already
            if len(quad.shape) == 3:
                quad = cv2.cvtColor(quad, cv2.COLOR_BGR2GRAY)
                
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(quad, (3, 3), 0)
            
            # Calculate Laplacian
            laplacian = cv2.Laplacian(blurred, cv2.CV_64F, ksize=kernel_size)
            abs_laplacian = np.absolute(laplacian)
            
            # Calculate histogram
            hist, bins = np.histogram(abs_laplacian, bins=256, range=(0, 256))
            
            # Calculate focus measures
            variance = np.var(abs_laplacian)
            percentile_90 = np.percentile(abs_laplacian, 90)
            
            # Calculate focus score
            focus_score = (variance + percentile_90) / 2
            
            quadrant_scores[name] = focus_score
        
        # Find best quadrant
        best_quadrant = max(quadrant_scores.items(), key=lambda x: x[1])
        
        return best_quadrant[1] 

    def isInFocus(self):
        while(self.isTakingImage):
            time.sleep(0.01)  # Avoid excessive CPU usage

        focusScore = self.calculate_quadrant_focus(self.lastImage)
        print("Focus Score:", focusScore)
        return focusScore

    def close(self):
        self.camera.Close()
        self.camera = None