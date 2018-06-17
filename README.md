# MagicHome-polyglot
This is the MagicHome Node Server for the ISY Polyglot interface.  
(c) fahrer16 aka Brian Feeney.  
MIT license. 

This was built on Debian 9 running on ESXi for ISY version 5.0.10 and polyglot v2 (https://github.com/Einstein42/udi-poly-template-python)
The original version for polyglot v1 is here: https://github.com/fahrer16/magichome-nodeserver

There are quite a few very inexpensive LED controllers that share the very simple TCP protocol used in the "MagicHome" app (https://play.google.com/store/apps/details?id=com.Zengge.LEDWifiMagicHome&hl=en).
This node server was rewritten from its original version to use the flux_led repository written by Daniel Hiversen (https://github.com/Danielhiversen/flux_led).


# Installation Instructions:
Same as most other ISY node servers:

1. Backup ISY (just in case)
2. Add Node Server into Polyglot v2 instance:
  * Follow instructions here: https://github.com/Einstein42/udi-polyglotv2/wiki/Creating-a-NodeServer
3. The nodeserver uses multicast discovery to discover compatible LED controllers on the local subnet.  The discovery process can sometimes miss bulbs, so the node server optionally allows adding static entries for LED's to be added despite discovery.  The format is as follows:
  * Optional: Key starting with "led".  Value: {"ip":"192.168.0.84", "mac":"F0FEAF241937"}  "mac" is MAC address without ":"
  * Optional: Key: "delay".  Value: float corresponding to desired delay, in seconds, between issuance of command to controller and querying controller status.  Defaults to 1.0 seconds.
   
The LED controllers should show the correct status now, hit "Query" if the status fields are empty.  The connection to the LED controllers drops out frequently for me (maybe my network or WiFi setup, maybe my code is flaky).  I've noticed using the MagicHome app while the node server is connected to the controllers causes the node server to lose connection.

Known Issues:
- Communication to the LED controllers seems flaky at times.  Preventing anything other than polyglot from communicating with the LED controllers seems to improve the issue.  I've done my testing with all LED controllers on an isolated VLAN without internet access.
- The availability of Warm White controls is based on whether the LED controller reports it has WW LED capability, which doesn't mean there's actually a Warm White LED actually connected to the controller.
 
Version History:
* 2.0.0: Rewritten for Polyglot v2.  Included support for Warm White LED's.  I need someone to test this since I don't have any Warm White LED's
* 2.0.1: Corrected "mhbool" definition in editor profile
* 2.0.3: Added delay before querying controller status following issuance of a command.  Added closure of server.json file after reading.