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
        pass
        #for node in self.nodes:
        #    self.nodes[node].longPoll()

    def poll(self):
        pass
        #for node in self.nodes:
        #    self.nodes[node].poll()

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

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
            if 'controllers' not in self.polyConfig['customParams']:
                if self.firstRun:
                    LOGGER.info('No "controllers" key found in polyglot configuration, not adding any additional LED controllers')
                    LOGGER.info('Note: A controllers key can be added to Polyglot configuration to add controllers regardless of discovery.  Value is in format of "[{\'ipaddr\': \'192.168.1.30\', \'id'': \'F0FEAF241937\'},{\'ipaddr\': \'192.168.1.90\', \'id\': \'F0FEAF92B115\'}]" where "id" is MAC address')
            else:
                _controllersConfig = self.polyConfig['customParams']['controllers']
                LOGGER.info('Parsing custom controller configuration (%s)', str(_controllersConfig))
                for d in _controllersConfig:
                    self._addNode(d)
        except Exception as ex:
            LOGGER.error('Error parsing "controllers" configuration from polyglot: %s', str(ex))
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
                LOGGING.debug('MagicHome LED with IP address "%s" and MAC address "%s" already in ISY', name, address)
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
        self.device = device

    def start(self):
        LOGGER.info("%s MagicHome LED ready", self.address)
        self.query()

    def setOn(self, command):
        _value = command.get('value')
        LOGGER.info('Received command to turn on %s.', self.name)
        if _value is not None:
            if _value == 0:
                return self.setOff()
            try:
                if self.device.mode == 'color':
                    _existing_color = self.device.getRgb()
                    self.device.setRgb(self,_existing_color[0],_existing_color[1],_existing_color[2],_value)
                elif device.mode == 'ww':
                    _existing_color = self.device.getRgbw()
                    self.device.setRgbw(self,_existing_color[0],_existing_color[1],_existing_color[2],_existing_color[3],_value)
                else:
                    self.device.turnOn()
            except Exception as ex:
                LOGGER.error('Error turning on %s to %i. %s', self.name, _value, str(ex))
        else:
            try:
                self.device.turnOn()
            except Exception as ex:
                LOGGER.error('Error turning on %s. %s', self.name, str(ex))
        self.update_info()
        return True

    def fastOn(self, command):
        LOGGER.info('Received Fast On Command for %s', self.name)
        return self.setOn(Value=100)

    def setOff(self, command):
        LOGGER.info('Received command to turn off %s.', self.name)
        try:
            self.device.turnOff()
            self.update_info()
        except Exception as ex:
            LOGGER.error('Error turning off %s. %s', self.name, str(ex))
        return True

    def fastOff(self, command):
        LOGGER.info('Received Fast Off Command for %s', self.name)
        return self.setOff()

    def setBrtDim(self, command):
        _cmd = command.get('cmd')
        LOGGER.info('Received %s command on %s', str(_cmd), self.name)
        try:
            _existing_brightness = int(self.device.brightness / 255. * 100.) #get brightness as 0-100%
            if _cmd == 'BRT':
                _brightness = _existing_brightness + 3
            else:
                _brightness = _existing_brightness - 3
            _brightness = int(_brightness / 100. * 255.) #convert brightness to 0-255
            if _brightness <= 0: return self.setOff()

            if self.device.mode == 'ww':
                _existing_color = self.device.getRgbw()
                self.device.setRgb(_existing_color[0],_existing_color[1],_existing_color[2],_existing_color[3],max(min(_brightness,255),0))
            elif self.device.mode == 'color':
                _existing_color = self.device.getRgb()
                self.device.setRgb(_existing_color[0],_existing_color[1],_existing_color[2],max(min(_brightness,255),0))
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
        except Exception as ex:
            LOGGER.error('Error executing %s command on %s (%s)', str(_cmd), self.name, str(ex))
            return False
        return True

    def setManual(self, command):
        _cmd = command.get('cmd')
        _val = int(command.get('value'))
        if self.device.mode == 'color':
            _existing_color = self.device.getRgb()
            _existing_color[3] = 0
        elif self.device.mode == 'ww':
            _existing_color = self.device.getRgbw()
        else:
            _existing_color = [0,0,0,0]

        _red = _val if _cmd == 'SETR' else _existing_color[0]
        _green = _val if _cmd == 'SETG' else _existing_color[1]
        _blue = _val if _cmd == 'SETB' else _existing_color[2]
        _white = _val if _cmd == 'SETW' else _existing_color[3]
        if (_red + _green + _blue + _white) ==  0: return self.setOff()
        LOGGER.info('Received manual change, updating %s to: R:%i G:%i, B:%i, W:%i', self.name, _red, _green, _blue, _white)
        try:
            if self.device.rgbwcapable and _white > 0:
                self.device.setRgbw(_red, _green, _blue, _white)
            else:
                self.device.setRgb(_red, _green, _blue)
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
        except Exception as  ex: 
            LOGGER.error('Error setting manual rgb on %s (cmd=%s, value=%s). %s', self.name, str(_cmd), str(_val), str(ex))
            return False
        return True

    def setRGB(self, command):
        _red = int(command.get('R.uom100'))
        _green = int(command.get('G.uom100'))
        _blue = int(command.get('B.uom100'))
        if (_red + _green + _blue) <= 0: return self.setOff()
        LOGGER.info('Received RGB Command, updating %s to: R:%i G:%i, B:%i', self.name, _red, _green, _blue)
        try:
            self.device.setRgb(_red, _green, _blue)
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
        except Exception as  ex: 
            LOGGER.error('Error setting RGB on %s (cmd=%s, value=%s). %s', self.name, str(_cmd), str(_val), str(ex))
            return False
        return True

    def setColor(self, command):
        _color = int(command.get('value'))
        _pct_brightness = self.device.brightness / 255. #get brightness as 0-1
        _red = int(COLORS[_color][1][0] * pct_brightness)
        _green = int(COLORS[_color][1][1] * pct_brightness)
        _blue = int(COLORS[_color][1][2] * pct_brightness)
        if (_red + _green + _blue) == 0: return self.setOff()
        try:
            self.device.setRgb(_red, _green, _blue)
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
            LOGGER.info('Received setColor command, changing %s color to %s', self.name, COLORS[_color][0])
        except Exception as  ex: 
            LOGGER.error('Error seting color on %s to %s. %s', self.name, str(_color), str(ex))
            return False
        return True

    def update_info(self):
        #Update Mode:
        _str_mode = self.device.mode
        if _str_mode == 'off':
            self.setDriver('GV5',0)
        elif _str_mode == 'color':
            self.setDriver('GV5',1)
        elif _str_mode == 'ww':
            self.setDriver('GV5',2)
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

        #Update Device Brightness
        if self.device.isOn:
            _brightness = int(self.device.brightness / 255.)
            self.setDriver('ST', _brightness)
        else:
            self.setDriver('ST',0)

        #Get Colors (if mode is 'color')
        if _str_mode == 'color':
            _color = self.device.getRgb()
            self.setDriver('GV1', _color[0])
            self.setDriver('GV2', _color[1])
            self.setDriver('GV3', _color[2])
        else:
            self.setDriver('GV1', 0)
            self.setDriver('GV2', 0)
            self.setDriver('GV3', 0)


    def query(self, command=""):
        LOGGER.debug('Querying %s', self.name)
        try:
            self.device.update_state()
            self.update_info()
            self.setDriver('GV4', True) #Connected
            self.reportDrivers()
        except Exception as ex:
            LOGGER.error('Error querying %s (%s)', self.name, str(ex))
            self.setDriver('GV4', False) #Connected = False

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
        super()
        _ww = self.device.getWarmWhite255() if _str_mode == 'ww' else 0
        self.setDriver('GV6', _ww)

    def setTemperature(self, command):
        _temp = int(command.get('value'))
        #Check that temperature is proper and in correct range (2700K-6500K)
        if _temp is None:
            LOGGER.error('Received Set Temperature Command on %s but no value supplied', self.name)
            return False
        if (_temp < 2700 or temp > 6500): 
            LOGGER.error('Received Set Temperature Command on %s but not within range of 2700-6500K (%i)', self.name, _temp)
            return False

        #Check that bulb brightness is proper, if it's too low, set it to 100% (255)
        _brightness = self.device.brightness
        if _brightness <= 0:
            _brightness = 255

        LOGGER.info('Received Set Temperature Command, updating %s to: %iK, brightness %i', self.name, _temp, _brightness)
        try:
            self.device.setWhiteTemperature(_temp, _brightness)
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
        except Exception as  ex: 
            LOGGER.error('Error setting Temperature on %s (cmd=%s, value=%s). %s', self.name, str(_cmd), str(_temp), str(ex))
            return False
        return True

    def setRGBW(self, command):
        _red = int(command.get('R.uom100'))
        _green = int(command.get('G.uom100'))
        _blue = int(command.get('B.uom100'))
        _white = int(command.get('W.uom100'))
        if (_red + _green + _blue + _white) <= 0: return self.setOff()
        LOGGER.info('Received RGBW Command, updating %s to: R:%i G:%i, B:%i, W:%i', self.name, _red, _green, _blue, _white)
        try:
            self.device.setRgbw(_red, _green, _blue, _white)
            if self.device.isOn: self.update_info() 
            else: self.SetOn()
        except Exception as  ex: 
            LOGGER.error('Error setting RGBW on %s (cmd=%s, value=%s). %s', self.name, str(_cmd), str(_val), str(ex))
            return False
        return True

    def setOn(self, command):
        super().setOn(self,command)

    def setOff(self, command):
        super().setOff(self,command)

    def fastOn(self, command):
        super().fastOn(self,command)

    def fastOff(self, command):
        super().fastOff(self,command)

    def query(self, command):
        super().query(self, command)

    def setBrtDim(self, command):
        super().query(self, command)

    def setColor(self, command):
        super().query(self, command)

    def setManual(self, command):
        super().setManual(self, command)

    def setRGB(self, command):
        super().setRGB(self, command)

    def longPoll(self):
        super().longPoll(self)

    def poll(self):
        super().poll(self)

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 51}, #BRIGHTNESS
               {'driver': 'GV1', 'value': 0, 'uom': 56}, #RED
               {'driver': 'GV2', 'value': 0, 'uom': 56}, #GREEN
               {'driver': 'GV3', 'value': 0, 'uom': 56}, #BLUE
               {'driver': 'GV3', 'value': 0, 'uom': 56}, #WHITE
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
