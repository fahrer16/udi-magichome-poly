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
2. Clone the MagicHome Node Server into the /.polyglot/nodeservers folder for the user that runs polyglot v2:
  * `Assuming you're logged in as the user that runs polyglot, cd cd ~/.polyglot/nodeservers
  * `git clone https://github.com/fahrer16/udi-magichome-poly.git
3. Install pre-requisites using install.sh script
  * 'chmod +x ./install.sh
  * 'install.sh
4. Add Node Server into Polyglot instance.
  * Follow instructions here, starting with "Open Polyglot": https://github.com/Einstein42/udi-polyglotv2/wiki/Creating-a-NodeServer 

The LED controllers should show the correct status now, hit "Query" if the status fields are empty.  The connection to the LED controllers drops out frequently for me (maybe my network or WiFi setup, maybe my code is flaky).  I've noticed using the MagicHome app while the node server is connected to the controllers causes the node server to lose connection.

Known Issues:
- Communication to the LED controllers seems flaky at times.  Preventing anything other than polyglot from communicating with the LED controllers seems to improve the issue.  I've done my testing with all LED controllers on an isolated VLAN without internet access.
- The availability of Warm White controls is based on whether the LED controller reports it has WW LED capability, which doesn't mean there's a Warm White LED actually connected to the controller.
 
Version History:
2.0.0: Rewritten for Polyglot v2.  Included support for Warm White LED's.  I need someone to test this since I don't have any Warm White LED's