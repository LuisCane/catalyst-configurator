# Catalyst Configurator

## Intro
This script is intended to automate the configuration of Cisco Catalyst switches via Telnet using a terminal access server. As it is writen it will find the model of a switch and match that model with a dictionary file, device-dict.json to get attributes and specs about that model. The config.json has some default configuration settings including host or IP address, port number, config skip, and debug mode. At the end, the script prints the specs of the switch and prompts you to clear the configs and reboot.

## Installation
Make the script executable.
```bash
chmod +x install.sh
```
Run the install.sh script.
```bash
./install.sh
```
or
```bash
sudo ./install.sh
```
If you run the script as root or with sudo, the script will be installed to ``/opt/catalyst-configurator`` and a symbolic link to ``catalyst-config.py`` will be created at ``/usr/bin/catalyst-config``. If you run the scrip without root privilege, the script will be installed to ``~/.bin/catalyst-configurator``.

## General Usage
You can use ``chmod +x catalyst-config.py`` in Linux to make the script executable or use ``python3 catalyst-config.py``.
```bash
catalyst-config.py --help

usage: catalyst-config.py [-h] [--host HOST] [--port PORT] [--no-config] [--debug]

Configure Cisco Catalyst Switches via Telnet and print Specs.

options:
  -h, --help   show this help message and exit
  --host HOST  the hostname or IP address to connect to
  --port PORT  the TCP port to connect to
  --no-config  Skip Switch Config.
  --debug      Enable Debugging mode.
```
``--no-config`` skips the config portion of the script and just prints the specs at the end.
``--debug`` activates a function that pauses the script at certain points.
When used with no arguments, the script will follow the default settings in config.json. It will try to connect to the hostname or IP in the file with the port number with config mode enabled and debug disabled.

## Device Dictionary
At some point I would like to add a function in the script that lets you add devices to the device-dict.json dictionary file when a model is not found in it. As it is now, the script just gets "none" variables and errors out. To add a device to the dictionary, copy the template item and adjust the specs as needed. Be sure to follow json formating.
