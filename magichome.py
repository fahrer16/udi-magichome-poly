#!/usr/bin/env python3
"""
This is a NodeServer for controlling magichome/flux-led style LED lights by fahrer16 (Brian Feeney)
Based on template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com
"""

import polyinterface
"""#NEED TO RENAME __main__ to flux_led"""
from flux_led import BulbScanner, WifiLedBulb
import sys
import os
import json
import math

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

# Changing these will not update the ISY names and labels, you will have to edit the profile.
COLORS = {
	0: ['RED', [255,0,0]],
	1: ['ORANGE', [255,165,0]],
	2: ['YELLOW', [255,255,0]],
	3: ['GREEN', [0,255,0]],
	4: ['CYAN', [0,255,255]],
	5: ['BLUE', [0,0,255]],
	6: ['PURPLE', [160,32,240]],
	7: ['PINK', [255,192,203]],
	8: ['WHITE', [255,255,255]],
	9: ['COLD_WHTE', [201,226,255]],
	10: ['WARM_WHITE', [255,147,41]],
	11: ['GOLD', [255,215,0]]
}

class Controller(polyinterface.Controller):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot.
    self.added: Boolean Confirmed added to ISY as primary node

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node): Adds Node to self.nodes and polyglot/ISY. This is called for you
                                 on the controller itself.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.firstRun = True
        self.name = 'MagicHome Controller'

    def start(self):
        LOGGER.info('Starting MagicHome LED Polyglot v2 NodeServer version {}'.format(VERSION))
        self.discover()

    def longPoll(self):
        self.query()

    def poll(self):
        pass
        #for node in self.nodes:
        #    self.nodes[node].poll()

    def query(self, command=None):
        for node in self.nodes:
            self.nodes[node].update_info()

    def update_info(self):
        pass #Nothing to update for controller

    def discover(self, *args, **kwargs):
        _success = False
        try:
            LOGGER.info('Discovering MagicHome LED Controllers...')
            _scanner = BulbScanner()
            _scanner.scan(timeout=5)
            _devices = _scanner.getBulbInfo()
            LOGGER.info('%i bulbs found. Checking status and adding to ISY', len(_devices))
            for d in _devices:
                self._addNode(d)
            _success = True
        except Exception as ex:
            LOGGER.error('Error running magichome discovery (%s)', str(ex))
        
        try:
            _items = 0
            self.discoveryTries = 0
            _params = self.polyConfig['customParams']
            for key,value in _params.items():
                _key = key.lower()
                if _key.startswith('led'):
                    _items += 1
                    try:
                        if 'ip' in value and 'mac' in value:
                            _value = json.loads(value)
                            _ip = _value['ip']
                            _mac = _value['mac'].lower().replace(':','')
                            d = {'ipaddr': _ip, 'id': _mac}
                            self._addNode(d)
                    except Exception as ex:
                        LOGGER.error('Error adding node from Polyglot configuration (%s): %s', str(value), str(ex))
            if _items == 0:
                LOGGER.info('NOTE: LED Controllers can be specified for addition even if not detected via discovery.  Add a custom configuration parameter to Polyglot for each LED controller with a key starting with "LED".  The value should be in the following format, note the use of double quotes: {"ip":"192.168.0.84", "mac":"F0FEAF241937"}  "mac" is the MAC address without colons.')
        except Exception as ex:
            LOGGER.error('Error processing custom node addition from Polyglot configuration: %s', str(ex))

        self.firstRun = False
        return _success

    def _addNode(self, d):
        try:
            name = 'mh ' + d['ipaddr'].replace('.',' ')
            address = str(d['id']).lower()
            address = address[-14:]
            if address not in self.nodes:
                led = WifiLedBulb(d['ipaddr'])
                if led.rgbwcapable:
                    LOGGER.info('Adding new MagicHome RGBW LED: %s(%s)', name, address)
                    self.addNode(MagicHomeWWLED(self, self.address, address, name, device = led))
                else:
                    LOGGER.info('Adding new MagicHome RGB LED: %s(%s)', name, address)
                    self.addNode(MagicHomeLED(self, self.address, address, name, device = led))
            else:
                LOGGER.debug('MagicHome LED with IP address "%s" and MAC address "%s" already in ISY', name, address)
                return False
        except Exception as ex:
            LOGGER.error('Error adding Bulb: %s', str(ex))
            return False
        return True
        

    id = 'controller'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2} #Built-in for polyglot v2, do not delete
              ]


class MagicHomeLED(polyinterface.Node):
    def __init__(self, parent, primary, address, name, device):
        super().__init__(parent, primary, address, name)
        self.brightness = 0
        self.red = 0 
        self.green = 0
        self.blue = 0
        self.white = 0
        self.device = device

    def start(self):
        LOGGER.info("%s MagicHome LED ready", self.address)
        self.update_info()

    def setOn(self, command=None):
        try:
            LOGGER.info('Received command to turn on %s.', self.address)
            _value = command.get('value')
            
            if _value is not None:
                _value = int(_value)
                if _value == 0:
                    return self.setOff()
                elif self.device.rgbwcapable:
                    _existing_color = self.device.getRgbw()
                    _max = max(_existing_color)
                    _red = _existing_color[0] / _max * 255. * _value / 100.
                    _green = _existing_color[1] / _max * 255. * _value / 100.
                    _blue = _existing_color[2] / _max * 255. * _value / 100.
                    _white = _existing_color[3] / _max * 255. * _value / 100.
                    LOGGER.debug('Setting %s to red=%s, green=%s, blue=%s, white=%s', str(_red), str(_green), str(_blue), str(_white))
                    self.device.setRgbw(_red, _green, _blue, _white)
                else:
                    _existing_color = self.device.getRgb()
                    _max = max(_existing_color)
                    _red = _existing_color[0] / _max * 255. * _value / 100.
                    _green = _existing_color[1] / _max * 255. * _value / 100.
                    _blue = _existing_color[2] / _max * 255. * _value / 100.
                    LOGGER.debug('Setting %s to red=%s, green=%s, blue=%s', str(_red), str(_green), str(_blue))
                    self.device.setRgb(_red, _green, _blue)    
        except Exception as ex:
            LOGGER.error('Error turning on %s (command=%s). %s', self.address, str(command), str(ex))
        
        try:
            self.device.turnOn()
        except Exception as ex:
            LOGGER.error('Error turning on %s. %s', self.address, str(ex))
        self.update_info()
        return True

    def fastOn(self, command=None):
        LOGGER.info('Received Fast On Command for %s', self.address)
        _cmd = {'value': 100}
        return self.setOn(_cmd)

    def setOff(self, command=None):
        LOGGER.info('Received command to turn off %s.', self.address)
        try:
            self.device.turnOff()
            self.update_info()
        except Exception as ex:
            LOGGER.error('Error turning off %s. %s', self.address, str(ex))
        return True

    def fastOff(self, command=None):
        LOGGER.info('Received Fast Off Command for %s', self.address)
        return self.setOff(command)

    def setBrtDim(self, command):
        _cmd = command.get('cmd')
        LOGGER.info('Received %s command on %s', str(_cmd), self.address)
        try:
            if _cmd == 'BRT':
                _brightness = self.brightness + 3
            else:
                _brightness = self.brightness - 3
            _brightness = max(min(brightness,100),0)
            if _brightness == 0: 
                return self.setOff()
            else:
                self.setOn(_brightness)
        except Exception as ex:
            LOGGER.error('Error executing %s command on %s: %s', str(_cmd), self.address, str(ex))
            return False
        return True

    def setManual(self, command):
        try:
            LOGGER.info('Received manual change command for %s, %s', self.address, str(command))
            _cmd = command.get('cmd')
            _val = int(command.get('value'))
            _red = _val if _cmd == 'SETR' else self.red
            _green = _val if _cmd == 'SETG' else self.green
            _blue = _val if _cmd == 'SETB' else self.blue

            if self.device.rgbwcapable:
                _white = _val if _cmd == 'SETW' else self.white
                self.device.setRgbw(_red, _green, _blue, _white)
                
            else:
                self.device.setRgb(r=_red, g=_green,b=_blue)
            self.update_info() 
        except Exception as  ex: 
            LOGGER.error('Error setting manual rgb on %s (cmd=%s, value=%s). %s', self.address, str(_cmd), str(_val), str(ex))
            return False
        return True        

    def setRGB(self, command):
        try:
            _red = int(command.get('R.uom100'))
            _green = int(command.get('G.uom100'))
            _blue = int(command.get('B.uom100'))
            if (_red + _green + _blue) <= 0: return self.setOff()
            LOGGER.info('Received RGB Command, updating %s to: R:%i G:%i, B:%i', self.address, _red, _green, _blue)
            self.device.setRgb(_red, _green, _blue)
            self.update_info() 
        except Exception as  ex: 
            LOGGER.error('Error setting RGB on %s (%s). %s', self.address, str(command), str(ex))
            return False
        return True

    def setColor(self, command):
        try:
            _color = int(command.get('value'))
            LOGGER.info('Received setColor command, changing %s color to %s', self.address, COLORS[_color][0])
            _pct_brightness = self.brightness / 100. if self.brightness > 0 else 1 #get brightness as 0-1, default to 100% if the brightness is 0 (light off)
            _red = int(COLORS[_color][1][0] * _pct_brightness)
            _green = int(COLORS[_color][1][1] * _pct_brightness)
            _blue = int(COLORS[_color][1][2] * _pct_brightness)
            self.device.setRgb(_red, _green, _blue)
            self.update_info() 
        except Exception as  ex: 
            LOGGER.error('Error seting color on %s (command = %s): %s', self.address, str(command), str(ex))
            return False
        return True

    def update_info(self):
        try:
            self.device.update_state() #query LED Controller
        except Exception as ex:
            LOGGER.error('Error updating device state for %s: %s', self.address, str(ex))
            return False

        try:           
            #Update Mode:
            _str_mode = self.device.mode
            if _str_mode == 'off' or not self.device.is_on:
                self.setDriver('GV5',0)
                self.setDriver('ST',0)
            elif _str_mode == 'color':
                self.setDriver('GV5',1)
                if self.device.rgbwcapable:
                    _color = self.device.getRgbw()
                    self.setDriver('GV1', _color[0])
                    self.setDriver('GV2', _color[1])
                    self.setDriver('GV3', _color[2])
                    self.setDriver('GV6', _color[3])
                    self.white = _color[3]
                else:
                    _color = self.device.getRgb()
                    self.setDriver('GV1', _color[0])
                    self.setDriver('GV2', _color[1])
                    self.setDriver('GV3', _color[2])
                self.red = _color[0]
                self.green = _color[1]
                self.blue = _color[2]
                self.brightness = math.ceil(max(_color) / 255. * 100.)
                self.setDriver('ST', self.brightness)
            elif _str_mode == 'ww' and self.device.rgbwcapable:
                self.setDriver('GV5',2)
                _ww = self.device.getWarmWhite255() if self.device.mode == 'ww' else 0
                self.setDriver('GV6', _ww)
                _brightness = int(math.ceil(_ww / 255. * 100.))
                self.setDriver('ST', _brightness)
            #TODO: Support for the following modes is not yet fully implemented:
            elif _str_mode == 'custom':
                self.setDriver('GV5',3)
            elif _str_mode == 'preset':
                self.setDriver('GV5',4)
            elif _str_mode == 'sunrise':
                self.setDriver('GV5',5)
            elif _str_mode == 'sunset':
                self.setDriver('GV5',6)
            elif _str_mode == 'default':
                self.setDriver('GV5',7)
            else: #unknown
                self.setDriver('GV5',8)

            self.setDriver('GV4', 1) #Connected
        except Exception as ex:
            LOGGER.error('Error updating device info for %s: %s', self.address, str(ex))
            self.setDriver('GV4', 0) #Connected = False


    def query(self, command=None):
        LOGGER.debug('Querying %s', self.address)
        self.update_info()

    def longPoll(self):
        self.query()

    def poll(self):
        pass
            
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 51}, #BRIGHTNESS
               {'driver': 'GV1', 'value': 0, 'uom': 56}, #RED
               {'driver': 'GV2', 'value': 0, 'uom': 56}, #GREEN
               {'driver': 'GV3', 'value': 0, 'uom': 56}, #BLUE
               {'driver': 'GV4', 'value': 0, 'uom': 2}, #Connected
               {'driver': 'GV5', 'value': 8, 'uom': 25} #Mode (Index)
              ]

    id = 'magichomeled'
    commands = {
                    'DON': setOn, 
                    'DOF': setOff, 
                    'DFON': fastOn, 
                    'DFOF': fastOff, 
                    'QUERY': query,
                    'BRT': setBrtDim, 'DIM': setBrtDim, 
                    'SET_COLOR': setColor, 
                    'SETR': setManual, 'SETG': setManual, 'SETB': setManual, 
                    'SET_RGB': setRGB
                }

class MagicHomeWWLED(MagicHomeLED): #Extendard standard MagicHomeLED class to include support for Warm White-capable bulbs
   
    def update_info(self): #Extend standard MagicHomeLED update_info method to include warm white 
        super().update_info()
        

    def setTemperature(self, command):
        _temp = int(command.get('value'))
        #Check that temperature is proper and in correct range (2700K-6500K)
        if _temp is None:
            LOGGER.error('Received Set Temperature Command on %s but no value supplied', self.address)
            return False
        if (_temp < 2700 or temp > 6500): 
            LOGGER.error('Received Set Temperature Command on %s but not within range of 2700-6500K (%i)', self.address, _temp)
            return False

        #Check that bulb brightness is proper, if it's too low, set it to 100% (255)
        _brightness = min(max(self.device.brightness / 100. * 255.,0),255)
        if _brightness == 0: _brightness = 255

        LOGGER.info('Received Set Temperature Command, updating %s to: %iK, brightness %i', self.address, _temp, _brightness)
        try:
            self.device.setWhiteTemperature(_temp, _brightness)
            self.SetOn()
            self.update_info()
        except Exception as  ex: 
            LOGGER.error('Error setting Temperature on %s (%s). %s', self.address, str(command), str(ex))
            return False
        return True

    def setRGBW(self, command):
        try:
            _red = int(command.get('R.uom100'))
            _green = int(command.get('G.uom100'))
            _blue = int(command.get('B.uom100'))
            _white = int(command.get('W.uom100'))
            if (_red + _green + _blue + _white) <= 0: return self.setOff()
            LOGGER.info('Received RGBW Command, updating %s to: R:%i G:%i, B:%i, W:%i', self.address, _red, _green, _blue, _white)
            self.device.setRgbw(_red, _green, _blue, _white)
            self.update_info() 
        except Exception as  ex: 
            LOGGER.error('Error setting RGBW on %s (%s). %s', self.address, str(command), str(ex))
            return False
        return True

    def setOn(self, command=None):
        super().setOn(command)

    def setOff(self, command=None):
        super().setOff(command)

    def fastOn(self, command=None):
        super().fastOn(command)

    def fastOff(self, command=None):
        super().fastOff(command)

    def query(self, command=None):
        super().query(command)

    def setBrtDim(self, command=None):
        super().setBrtDim(command)

    def setColor(self, command):
        super().setColor(command)

    def setManual(self, command):
        super().setManual(command)

    def setRGB(self, command):
        super().setRGB(command)

    def longPoll(self):
        super().longPoll(self)

    def poll(self):
        super().poll(self)

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 51}, #BRIGHTNESS
               {'driver': 'GV1', 'value': 0, 'uom': 56}, #RED
               {'driver': 'GV2', 'value': 0, 'uom': 56}, #GREEN
               {'driver': 'GV3', 'value': 0, 'uom': 56}, #BLUE
               {'driver': 'GV6', 'value': 0, 'uom': 56}, #WHITE
               {'driver': 'GV4', 'value': 0, 'uom': 2}, #Connected
               {'driver': 'GV5', 'value': 8, 'uom': 25} #Mode (Index)
              ]

    id = 'magichomewwled'
    commands = {
                    'DON': setOn, 
                    'DOF': setOff, 
                    'DFON': fastOn, 
                    'DFOF': fastOff, 
                    'QUERY': query,
                    'BRT': setBrtDim, 'DIM': setBrtDim, 
                    'SET_COLOR': setColor, 
                    'SETR': setManual, 'SETG': setManual, 'SETB': setManual, 'SETW': setManual,
                    'SET_RGB': setRGB,
                    'SET_RGBW': setRGBW,
                    'SET_TEMP': setTemperature
                }


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('MagicHome')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
