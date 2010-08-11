"""
Name: bridge.py
Desc: Provides a Bridge and Mote class for working with SkyMote bridges and 
      motes.
"""
from LabJackPython import *

if os.name == "nt":
    if skymoteLib is None:
        raise ImportError("Couldn't load liblabjackusb.dll. Please install, and try again.")
        
    


class Bridge(Device):
    """
    Bridge class for working with wireless bridges
    
    >>> import bridge
    >>> d = bridge.Bridge()
    """
    # ------------------ Object Functions ------------------
    # These functions are part of object interaction in python
    
    def __init__(self, handle = None, autoOpen = True, **kargs):
        Device.__init__(self, None, devType = 0x501)
    
        self.handle = handle
        
        if 'localId' in kargs:
            self.localId = kargs['localId']
        else:
            self.localId = None
        
        if 'serial' in kargs:
            self.serialNumber = kargs['serial']
        else:
            self.serialNumber = None
        
        self.ethernetFWVersion = None
        self.usbFWVersion = None
        self.deviceName = "SkyMote Bridge"
        self.devType = 0x501
        self.unitId = 0
        self.debug = True
        self.modbusPrependZeros = False
        
        if autoOpen:
            self.open(**kargs)
        
    def open(self, firstFound = True, localId = None, serial = None, devNumber = None, handleOnly = False, LJSocket = "localhost:6000"): #"
        Device.open(self, 0x501, firstFound = firstFound, localId = localId, serial = serial, devNumber = devNumber, handleOnly = handleOnly, LJSocket = LJSocket)
    
    if os.name == "nt":
        def _readFromUDDriver(self, numBytes, stream, modbus):
            newA = (ctypes.c_byte*numBytes)()
            readBytes = skymoteLib.LJUSB_IntRead(self.handle, 0x81, ctypes.byref(newA), numBytes)
            return [(newA[i] & 0xff) for i in range(readBytes)]
            
        def _writeToUDDriver(self, writeBuffer, modbus):
            newA = (ctypes.c_byte*len(writeBuffer))(0) 
            for i in range(len(writeBuffer)):
                newA[i] = ctypes.c_byte(writeBuffer[i])
            
            writeBytes = skymoteLib.LJUSB_IntWrite(self.handle, 1, ctypes.byref(newA), len(writeBuffer))
            
            if(writeBytes != len(writeBuffer)):
                raise LabJackException( "Could only write %s of %s bytes." % (writeBytes, len(writeBuffer) ) )
    
    def read(self, numBytes, stream = False, modbus = False):
        result = Device.read(self, 64, stream, modbus)
        return result[:numBytes]
        
    def spontaneous(self):
        while True:
            packet = self.read(64, stream = True)
            localId = packet[6]
            packet = struct.pack("B"*len(packet), *packet)
            rxLqi, txLqi, battery, temp, light, motion, sound = struct.unpack(">"+"f"*7, packet[9:37])
            
            results = dict()
            results['localId'] = localId
            results['RxLQI'] = rxLqi
            results['TxLQI'] = txLqi
            results['Battery'] = battery
            results['Temp'] = temp
            results['Light'] = light
            results['Motion'] = motion
            results['Sound'] = sound
            
            yield results
    
    def readRegister(self, addr, numReg = None, format = None, unitId = None):
        if unitId is None:
            return Device.readRegister(self, addr, numReg, format, self.unitId)
        else:
            return Device.readRegister(self, addr, numReg, format, unitId)
            
    def writeRegister(self, addr, value, unitId = None):
        if unitId is None:
            return Device.writeRegister(self, addr, value, unitId = self.unitId)
        else:
            return Device.writeRegister(self, addr, value, unitId = unitId)
    
    # ------------------ Convenience Functions ------------------
    # These functions call read register for you. 
    def readSerialNumber(self):
        self.serialNumber = self.readRegister(65001)
        return self.serialNumber
        
    def readNumberOfMotes(self):
        return self.readRegister(59200, numReg = 2, format = '>I')
        
    def ethernetFirmwareVersion(self):
        left, right = self.readRegister(56000, format = '>BB')
        self.ethernetFWVersion = "%s.%02d" % (left, right)
        return "%s.%02d" % (left, right)
    
    def usbFirmwareVersion(self):
        left, right = self.readRegister(57000, format = '>BB')
        self.usbFWVersion = "%s.%02d" % (left, right)
        return "%s.%02d" % (left, right)
        
    def mainFirmwareVersion(self):
        left, right = self.readRegister(65006, format = ">BB")
        self.mainFWVersion = "%s.%02d" % (left, right)
        return "%s.%02d" % (left, right)
    
    def usbBufferStatus(self):
        return self.readRegister(57001)
    
    def numUSBRX(self):
        return self.readRegister(57002, numReg = 2, format = '>I')
        
    def numUSBTX(self):
        return self.readRegister(57004, numReg = 2, format = '>I')
        
    def numPIBRX(self):
        return self.readRegister(57006, numReg = 2, format = '>I')
        
    def numPIBTX(self):
        return self.readRegister(57008, numReg = 2, format = '>I')
        
    def lastUsbError(self):
        return self.readRegister(57010)
    
    def dmOverflows(self):
        return self.readRegister(57011)
        
    def numPibTos(self):
        return self.readRegister(57014)
        
    def numUsbTos(self):
        return self.readRegister(57015)
    
    def vUsb(self):
        return self.readRegister(57050, numReg = 2, format = '>f')
    
    def vJack(self):
        return self.readRegister(57052, numReg = 2, format = '>f')
    
    def vSt(self):
        return self.readRegister(57054, numReg = 2, format = '>f')
    
    # ------------------ Mote Functions ------------------
    # These functions help you work with the motes.
    
    def listMotes(self):
        numMotes = self.readRegister(59200, numReg = 2, format = '>I')
        
        if numMotes == 0:
            return []
        
        connectedMotes = []
        
        moteIds = self.readRegister(59202, numReg = numMotes, format = ">" + "H" *numMotes )
        if isinstance(moteIds, list):
            for moteId in moteIds:
                connectedMotes.append(Mote(self, moteId))
            
            return connectedMotes
        else:
            return [Mote(self, moteIds)]
        
    def makeMote(self, moteId):
        return Mote(self, moteId)
    


class Mote(object):
    # ------------------ Object Functions ------------------
    # These functions are part of object interaction in python
    def __init__(self, bridge, moteId):
        self.bridge = bridge
        self.moteId = moteId
        self.deviceName = "SkyMote Mote"
        
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return "<Mote Object with ID = %s>" % self.moteId
        
    def readRegister(self, addr, numReg = None, format = None):
        return self.bridge.readRegister(addr, numReg = numReg, format = format, unitId = self.moteId)
    
    def writeRegister(self, addr, value):
        return self.bridge.writeRegister(addr, value, unitId = self.moteId)
        
    def getName(self):
        """
        Name: Device.getName()
        Args: None
        Desc: Returns the name of a device.
              Always returns a unicode string.
              Works as of the following firmware versions:
              U6 - 1.00
              U3 - 1.22
              UE9 - 2.00
        
        >>> d = u3.U3()
        >>> d.open()
        >>> d.getName()
        u'My LabJack U3'
        """
        name = list(self.readRegister(58000, format='B'*48, numReg = 24))
        
        if name[1] == 3:
            # Old style string
            name = "My %s" % self.deviceName
            print "Old UTF-16 name detected, replacing with %s" % name
            self.setName(name)
            name = name.decode("UTF-8")
        else:
            end = name.index(0x00)
            name = struct.pack("B"*end, *name[:end]).decode("UTF-8")
        
        return name
        
    def setName(self, name = "My LabJack U3"):
        """
        Name: Device.setName(name = ""My LabJack U3")
        Args: name, the name you'd like to assign the the U3
        Desc: Writes a new name to the device.
              Names a limited to 30 characters or less.
              Works as of the following firmware versions:
              U6 - 1.00
              U3 - 1.22
              UE9 - 2.00
        
        >>> d = u3.U3()
        >>> d.open()
        >>> d.getName()
        u'My LabJack U3'
        >>> d.setName("Johann")
        >>> d.getName()
        u'Johann'
        """
        strLen = len(name)
        
        if strLen > 47:
            raise LabJackException("The name is too long, must be less than 48 characters.")
        
        newname = name.encode('UTF-8')
        bl = list(struct.unpack("B"*strLen, newname)) + [0x00]
        strLen += 1
        
        if strLen%2 != 0:
            bl = bl + [0x00]
            strLen += 1
        
        bl = struct.unpack(">"+"H"*(strLen/2), struct.pack("B" * strLen, *bl))
        
        self.writeRegister(58000, list(bl))

    name = property(getName, setName)
        
    def close(self):
        self.bridge = None
    
    def mainFirmwareVersion(self):
        left, right = self.readRegister(65006, format = ">BB")
        self.mainFWVersion = "%s.%02d" % (left, right)
        return "%s.%02d" % (left, right)
    
    # ------------------ Convenience Functions ------------------
    # These functions call read register for you. 
    
    def startRapidMode(self, minutes = 1):
        # Sends the command to put a bridge in rapid mode.
        self.writeRegister(59990, minutes)
        
    def stopRapidMode(self):
        # Sends the command to disable rapid mode.
        self.startRapidMode(0)
        
    def setCheckinInterval(self, milliseconds=1000):
        self.writeRegister(50102, milliseconds)
        
    def readCheckinInterval(self):
        return self.readRegister(50102)
    
    def sensorSweep(self):
        """
        Performs a sweep of all the sensors on the sensor mote.
        """
        rxLqi, txLqi, battery, temp, light, motion, sound = self.readRegister(12000, numReg = 14, format = ">" + "f"*7)
        
        results = dict()
        results['RxLQI'] = rxLqi
        results['TxLQI'] = txLqi
        results['Battery'] = battery
        results['Temp'] = temp
        results['Light'] = light
        results['Motion'] = motion
        results['Sound'] = sound
        
        return results
        
    def panId(self):
        return self.readRegister(50000)
        
    def sleepTime(self):
        return self.readRegister(50100, numReg = 2, format = ">I")