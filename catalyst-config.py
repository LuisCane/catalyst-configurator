#!/usr/bin/env python3
# SSH Version

import argparse
import getpass
import inspect
import json
import logging
import os
import re
import select
import time
import paramiko

def parse_arguments():
    #Default settings
    default_settings = {
        "host": "nr-rt.comprenew.arpa",
        "port": 2001,
        "username": "script",
        "password": "32453245",
        "sshkey": "",
        "config": True,
        "debug": True
    }

    parser = argparse.ArgumentParser(description='Configure Cisco Catalyst Switches via SSH and print Specs.')
    parser.add_argument('--host', dest='host', default=default_settings["host"], help='the Hostname or IP address to connect to')
    parser.add_argument('--port', dest='port', type=int, default=default_settings["port"], help='the TCP port to connect to')
    parser.add_argument('--username', dest='username', default=default_settings["username"], help='the Username for SSH')
    parser.add_argument('--password', dest='password', default=default_settings["password"], help='the Password for SSH')
    parser.add_argument('--ssh-key', dest='sshkey', default=default_settings["sshkey"], help='Full path to SSH key')
    parser.add_argument('--no-config', action='store_true', default=default_settings["config"], help='Skip Switch Config.')
    parser.add_argument('--debug', action='store_true', default=default_settings["debug"], help='Enable Debugging mode.')
    args = parser.parse_args()

    if not args.host:
        args.host = input("Enter host name or IP address: ")
    if not args.port:
        args.port = input("Enter port: ")
    if not args.username:
        args.username = input("Enter Username: ")
    if not args.password and not args.sshkey:
        args.password = getpass.getpass("Enter password: ")
    if not args.sshkey and args.password:
        args.sshkey = input("Enter full path to SSH Key file (leave blank for password authentication): ")

    return args

# Set user mode
userMode = "userExec"

def ask_yes_no(prompt):
    """
    Ask the user a yes or no question and return their response as a boolean.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        bool: True if the user answered yes, False otherwise.
    """
    while True:
        response = input(prompt).strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no", ""]:
            return False
        else:
            print("Invalid response. Please answer yes or no.")

def initialConnection(host, port, username, password, sshkey, debug):
    debugMode(debug)
    if debug:
        # Enable verbose output for paramiko
        logging.basicConfig(level=logging.DEBUG)

    global ssh
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if sshkey:
        try:
            private_key = paramiko.RSAKey.from_private_key_file(sshkey, password=None)
            transport = ssh.get_transport()
            transport.set_algorithms(look_for_keys=False, allow_agent=False, pubkey_algs=['ssh-rsa'])
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                pkey=private_key,
                timeout=10,
                look_for_keys=False,
                allow_agent=False
            )
            print(f"Successfully connected to {host} using SSH key authentication.")
            
        except IOError:
            print(f"IO Error")
            exit()
        except paramiko.PasswordRequiredException:
            print(f'Password Required')
            exit()
        except paramiko.SSHException:
            print(f"Key file is invalid.")
            exit()
        except:
            print(f"Could not connect to {host} using SSH key authentication.")
            exit()
    else:
        try:
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                look_for_keys=False,
                allow_agent=False
            )
            print(f"Successfully connected to {host} using password authentication.")

        except paramiko.BadHostKeyException:
            print(f"Bad Host Key Exception.")
            exit()
        except paramiko.AuthenticationException:
            print(f"Authentication failed when connecting to {host}.")
            exit()
        except:
            print(f"Could not connect to {host} using password authentication.")
            exit()
    global channel
    channel = ssh.invoke_shell()

def sendCMD(cmd):
    channel.send(f"{cmd}")
    # Read the output and print it to the console
    time.sleep(1)
    output = outputProc()
    print(output)
    return output

def outputProc(timeout=2):
    if channel.recv_ready():
        output = channel.recv(65535).decode("utf-8")
    else:
        # Wait for data to become available on the channel
        if select.select([channel], [], [], timeout)[0]:
            output = channel.recv(65535).decode("utf-8")
        else:
            output = ""
    return output

def waitForBoot(debug):
    debugMode(debug)
    # Wait for Boot sequence.
    output = outputProc()
    print(output)
    prev_output = output
    same_count = 0
    while same_count < 30:
        output = outputProc()
        output += sendCMD("\r")
        configDialoguePrompt = "Would you like to enter the initial configuration dialog? [yes/no]:"
        try:
            if configDialoguePrompt in output:
                same_count = 31
                sendCMD("n\r")
            elif "Switch>" in output:
                same_count = 31
            elif "Switch#" in output:
                same_count = 31
            elif "Switch(config)#" in output:
                sendCMD("end\r")
                same_count = 31
            else:
                print(output)
                print("Waiting for boot sequence..." + str(same_count) + "/30")
        except:
            if configDialoguePrompt in output:
                same_count = 31
                sendCMD("n\r")
            elif "Switch>" in output:
                same_count = 31
            elif "Switch#" in output:
                same_count = 31
            elif "Switch(config)#" in output:
                sendCMD("end\r")
                same_count = 31
            else:
                print(output)
                print("Waiting for boot sequence..." + str(same_count) + "/30")
        if output == prev_output:
            same_count += 1
        else:
            prev_output = output
            same_count = 0
    # Send a carriage return signal and print the output to the console
    global userMode
    output = sendCMD("\r")
    if "Switch>" in output:
        userMode = "userExec"
    elif "Switch#" in output:
        userMode = "privExec"
    elif "Switch(config)#" in output:
        sendCMD("end\r")
        userMode = "userExec"
    else:
        print("Check Prompt")
        input("Press Enter to Continue.")
    print("User mode is: ", userMode)

def getSwitchModel(debug):
    debugMode(debug)
    global switchModel
    # Enter show version command and advance through the pages
    output = sendCMD("show version\r")
    output += sendCMD(" ")
    output += sendCMD(" ")
    modelMatch = re.search(r"WS-C\D?\d{4}\D?\D?-\d{1,2}\D?\D\D?-?\D?\D?$", output, re.MULTILINE)
    if modelMatch:
        switchModel = modelMatch.group(0).strip()
        print("Switch Model: ", switchModel)
        return switchModel
    else:
        modelMatch = re.search(r"WS-C\D?\d{4}\D?\D?-\d{1,2}\D?\D\w?-?\w?", output, re.MULTILINE)
        if modelMatch:
            switchModel = modelMatch.group(0).strip()
            print("Switch Model: ", switchModel)
            return switchModel
        else:
            switchModel = "Switch-Not-Found"
            print("Switch Model: ", switchModel)
            return switchModel

def getSwitchIOS(debug):
    debugMode(debug)
    global switchIOS
    # Enter show version command and advance through the pages
    output = sendCMD("show version\r")
    output += sendCMD(" ")
    output += sendCMD(" ")
    output += sendCMD(" ")
    isIOSXEMatch = re.search(r"(IOS-XE)", output, re.MULTILINE)
    if isIOSXEMatch:
        isIOSXE = True
    else:
        isIOSXE = False
    if isIOSXE:
        osImageMatch = re.search(r"Catalyst\sL3\sSwitch\sSoftware\s\W(\w+-\w+-M)\W,\sVersion\s(\d+.\d+.\d+\w+).?\sRELEASE\sSOFTWARE", output, re.MULTILINE)
    else:
        osImageMatch = re.search(r"Software\s\W(C\D?\d{4}\w?-\w+-\w)\W,\sVersion\s+(\d+\.\d+)\W\d?\d?\W\w+,", output, re.MULTILINE)
    if osImageMatch:
        switchImage = osImageMatch.group(1).strip()
    else:
        switchImage = "Switch Image Not Found."
        print("Switch OS Image not found in output.")
    if osImageMatch:
        switchVer = osImageMatch.group(2).strip()
    else:
        switchVer = "IOS Version Not Found."
        print("Switch OS Image not found in output.")
    
    switchIOS = (switchImage, switchVer)
    print("SwitchIOS: ", switchIOS)
    return switchIOS

def get_switch_attributes(model):
    try:
        with open("device-dict.json", "r") as f:
            device_dict = json.load(f)
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(script_dir, "device-dict.json"), "r") as f:
                device_dict = json.load(f)
        except FileNotFoundError:
            try:
                home_dir = os.path.expanduser("~")
                with open(os.path.join(home_dir, ".bin", "catalyst-configurator", "device-dict.json"), "r") as f:
                    device_dict = json.load(f)
            except FileNotFoundError:
                with open("/opt/catalyst-configurator/device-dict.json", "r") as f:
                    device_dict = json.load(f)

    return device_dict.get("switches", {}).get(model, {})

def get_module_attributes(model):
    try:
        with open("device-dict.json", "r") as f:
            device_dict = json.load(f)
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(script_dir, "device-dict.json"), "r") as f:
                device_dict = json.load(f)
        except FileNotFoundError:
            try:
                home_dir = os.path.expanduser("~")
                with open(os.path.join(home_dir, ".bin", "catalyst-configurator", "device-dict.json"), "r") as f:
                    device_dict = json.load(f)
            except FileNotFoundError:
                with open("/opt/catalyst-configurator/device-dict.json", "r") as f:
                    device_dict = json.load(f)

    return device_dict.get("modules", {}).get(model, {})

def getSwitchInventory(debug):
    debugMode(debug)
    output = sendCMD("show inventory\r")
    output += sendCMD(" ")
    output += sendCMD("\r")
    return output

def collectSwitchInfo(debug):
    debugMode(debug)
    global switchModel
    switchModel = getSwitchModel(debug)
    global switchIOS
    switchIOS = getSwitchIOS(debug)
    attributesSwitch = get_switch_attributes(switchModel)
    if not attributesSwitch:
        print(f"Switch Model not in the dictionary file. Please add this model, {switchModel}, to the device-dict.json file.")
        quit()
    global specTagModel
    specTagModel = attributesSwitch.get('specTagModel')
    global oneGigAccess
    oneGigAccess = attributesSwitch.get('oneGigAccess')
    global tenGigAccess
    tenGigAccess = attributesSwitch.get('tenGigAccess')
    global oneGigUplink
    oneGigUplink = attributesSwitch.get('oneGigUplink')
    global tenGigUplink
    tenGigUplink = attributesSwitch.get('tenGigUplink')
    global tenGigX2
    tenGigX2 = 0
    global OOBE
    OOBE = attributesSwitch.get('OOBE')
    global OOBE_Speed
    OOBE_Speed = attributesSwitch.get('OOBE_Speed')
    global modularStacking
    modularStacking = attributesSwitch.get('modularStacking')
    global fixedStacking
    fixedStacking = attributesSwitch.get('fixedStacking')
    global modularUplink
    modularUplink = attributesSwitch.get('modularUplink')
    global fixedUplink
    fixedUplink = attributesSwitch.get('fixedUplink')
    global powerOverEthernet
    powerOverEthernet = attributesSwitch.get('powerOverEthernet')
    global multiLayer
    multiLayer = attributesSwitch.get('multiLayer')
    global Memory
    Memory = attributesSwitch.get('Memory')
    global Storage
    Storage = attributesSwitch.get('Storage')
    global externalPower
    externalPower = attributesSwitch.get('externalPower')
    global redundantPower
    redundantPower = attributesSwitch.get('redundantPower')
    global baseprice
    baseprice = attributesSwitch.get('baseprice')
    global management
    management = attributesSwitch.get('management')
    global usb
    usb = attributesSwitch.get('usb')
    global stackingSwitch
    stackingSwitch = modularStacking or fixedStacking
    global modularSwitch
    modularSwitch = modularStacking or modularUplink

def collectModuleInfo(debug):
    debugMode(debug)
    global installedUplinkMod1
    installedUplinkMod1 = "none"
    global installedUplinkMod2
    installedUplinkMod2 = "none"
    global uplinkX2
    uplinkX2 = False
    if "3750E" in switchModel or "3560E" in switchModel:
        uplinkX2 = True
        global tenGigX2
        tenGigX2 = 2
    global installedStackMod
    installedStackMod = "none"
    global modulePrice
    modulePrice = "$0"
    global moduleType
    moduleType = "NA"
    global forSeries
    forSeries = "NA"
    global oneGigPorts
    oneGigPorts = 0
    global tenGigPorts
    tenGigPorts = 0
    global stackPorts
    stackPorts = 0
    if modularUplink:
        if uplinkX2:
            moduleCT = 2
        else:
            moduleCT = 1
        print("Switch has Modular Uplink Feature.")
        switchInventory = getSwitchInventory(debug)
        print(switchInventory)
        installedUplinkMod1 = input("If a module is installed, enter the model here or press Enter for none: ").strip()
        if installedUplinkMod1 in [""]:
            installedUplinkMod1 = "none"
        else:
            attributesModule = get_module_attributes(installedUplinkMod1)
            if not attributesModule:
                print(f"Module Model not in the dictionary file. Please add this model, {installedUplinkMod1}, to the device-dict.json file.")
            moduleType = attributesModule.get('moduleType')
            forSeries = attributesModule.get('forSeries')
            oneGigPorts = attributesModule.get('oneGigPorts')
            tenGigPorts = attributesModule.get('tenGigPorts')
            modulePrice = attributesModule.get('modulePrice')
        if moduleCT == 2:
            installedUplinkMod2 = input("If a second module is installed, enter the model here or press Enter for none: ").strip()
            if installedUplinkMod2 in [""]:
                installedUplinkMod2 = "none"
            else:
                attributesModule = get_module_attributes(installedUplinkMod2)
                if not attributesModule:
                    print(f"Module Model not in the dictionary file. Please add this model, {installedUplinkMod2}, to the device-dict.json file.")
                oneGigPorts += attributesModule.get('oneGigPorts')
                tenGigPorts += attributesModule.get('tenGigPorts')
    if modularStacking:
        print("Switch has Modular Stacking Feature.")
        switchInventory = getSwitchInventory(debug)
        print(switchInventory)
        installedStackMod = input("If a module is installed, enter the model here or press Enter for none: ").strip()
        if installedStackMod in [""]:
            installedStackMod = "none"
        else:
            attributesModule = get_module_attributes(installedStackMod)
            moduleType = attributesModule.get('moduleType')
            forSeries = attributesModule.get('forSeries')
            stackPorts = attributesModule.get('stackPorts')
            modulePrice = attributesModule.get('modulePrice')

def enterConfigMode():
    global userMode
    # Enter privileged exec mode "enable"
    if userMode == "userExec":
        sendCMD("enable\r")
        userMode = "privExec"
        sendCMD("config terminal\r")
        userMode = "globalConfig"
    elif userMode == "privExec":
        # Enter global config mode
        if userMode == "privExec":
            sendCMD("configure terminal\r")
            userMode = "globalConfig"
    else:
        print("Check User Mode")
        input("Press Enter to continue.")

def commonSwitchConfig(debug):
    debugMode(debug)
    if userMode != "globalConfig":
        enterConfigMode()
    # Set line console to logging synchronous
    sendCMD("line con 0\r")
    sendCMD("logg sync\r")
    sendCMD("exit\r")
    # Create Vlans
    sendCMD("vlan 10\r")
    sendCMD("vlan 108\r")
    sendCMD("exit\r")

def configure_switch(debug):
    debugMode(debug)
    global userMode
    # Determine the interface range command for the access ports
    interface_access = ""
    interface_uplink = ""
    # Determine OOBE Management port if any.
    if OOBE == True:
        if "3850" in switchModel or "3650" in switchModel:
            interface_OOBE = ""
            if OOBE_Speed == "fe":
                interface_OOBE = f"interface f0/0\r"
            elif OOBE_Speed == "ge":
                interface_OOBE = f"interface g0/0\r"
        else:
            interface_OOBE = ""
            if OOBE_Speed == "fe":
                interface_OOBE = f"interface f0\r"
            elif OOBE_Speed == "ge":
                interface_OOBE = f"interface g0\r"
            else:
                interface_OOBE = f"interface e0\r"

        

    # Configure stacking switches with fixed uplink ports.
    if stackingSwitch and fixedUplink:
        # Configure gigabit stacking switches with fixed gigabit uplink ports.
        if tenGigAccess == 0 and tenGigUplink == 0:
            access_ports = (oneGigAccess + (oneGigUplink - 1))
            uplink_port = (access_ports + 1)
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface g1/0/{uplink_port}\r"
        
        # Configure gigabit stacking switches with fixed gigabit and 1-gig uplink ports.
        elif tenGigAccess == 0 and (0 < tenGigUplink < 4) and ("3650" in switchModel):
            access_ports = (oneGigAccess)
            uplink_access_ports = (oneGigUplink)
            uplink_ports = (tenGigUplink + 2)
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports} ,g1/1/1-{uplink_access_ports}\r"
            interface_uplink = f"interface range te1/1/3-{uplink_ports}\r"

        # Configure gigabit stacking switches with fixed gigabit and 1-gig uplink ports.
        elif tenGigAccess == 0 and (0 < tenGigUplink < 4):
            access_ports = (oneGigAccess + (oneGigUplink))
            module_access_ports = (oneGigUplink)
            uplink_ports = tenGigUplink
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports} ,g1/0/1-{module_access_ports}\r"
            interface_uplink = f"interface range te1/0/1-{uplink_ports}\r"
        
        # Configure gigabit stacking switches with fixed ten gig uplink ports.
        elif (tenGigAccess == 0) and (tenGigUplink == 4) and ("3650" in switchModel):
            access_ports = (oneGigAccess)
            uplink_ports = tenGigUplink
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface range te1/1/1-{uplink_ports}\r"
    

        # Configure gigabit stacking switches with fixed ten gig uplink ports.
        elif tenGigAccess == 0 and tenGigUplink == 4:
            access_ports = (oneGigAccess)
            uplink_ports = tenGigUplink
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface range te1/0/1-{uplink_ports}\r"
    
    # Configure stacking switches with X2 uplinks.
    elif stackingSwitch and uplinkX2:
        if installedUplinkMod1 == "none" and installedUplinkMod2 == "none":
            access_ports = (oneGigAccess - 1)
            uplink_port = (oneGigAccess)
            
            # Generate the interface range command for stacking switches with no uplinks.
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface g1/0/{uplink_port}\r"
        
        # Configure gigabit stacking switches with twingig modules installed.
        elif tenGigAccess == 0 and tenGigPorts == 0:
            access_ports = (oneGigAccess)
            access_ports += (oneGigPorts - 1)
            uplink_port = (oneGigAccess + 4)
           
            # Generate the interface range command for stacking switches with twingig modules installed.
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface g1/0/{uplink_port}\r"

        # Configure gigabit stacking switches with twingig and 10gig modules installed.
        elif tenGigAccess == 0 and (0 < tenGigPorts <= 2):
            access_ports = (oneGigAccess + 4)
            uplink_ports = 2
           
            # Generate the interface range command for stacking switches with twingig and/or 10gig  modules installed.
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface range  te1/0/1-{uplink_ports}\r"

    # Configure stacking switches with modular uplinks.
    elif stackingSwitch and modularUplink:
        # Configure gigabit stacking switches with no module installed.
        if installedUplinkMod1 == "none":
            access_ports = (oneGigAccess - 1)
            uplink_port = (oneGigAccess)
            
            # Generate the interface range command for stacking switches with no uplinks.
            interface_access = f"interface range g1/0/1-{access_ports}\r"
            interface_uplink = f"interface g1/0/{uplink_port}\r"
        
        # Configure gigabit stacking switches with gigabit module installed.
        elif tenGigAccess == 0 and tenGigPorts == 0:
            access_ports = (oneGigAccess)
            module_access_ports = (oneGigPorts - 1)
            uplink_port = (oneGigPorts)
           
            # Generate the interface range command for stacking switches with gigabit module installed.
            interface_access = f"interface range g1/0/1-{access_ports} ,g1/1/1-{module_access_ports}\r"
            interface_uplink = f"interface g1/1/{uplink_port}\r"
        
        # Configure gigabit stacking switches with gigabit/10 gig module installed.
        elif tenGigAccess == 0 and (0 < tenGigPorts < 4) and ("3850" in switchModel):
            access_ports = (oneGigAccess)
            module_access_ports = (oneGigPorts)
            uplink_ports = (tenGigPorts + 2)
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports} ,g1/1/1-{module_access_ports}\r"
            interface_uplink = f"interface range te1/1/3-{uplink_ports}\r"

        # Configure gigabit stacking switches with gigabit/10 gig module installed.
        elif tenGigAccess == 0 and (0 < tenGigPorts < 4):
            access_ports = (oneGigAccess)
            module_access_ports = (oneGigPorts)
            uplink_ports = tenGigPorts
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g1/0/1-{access_ports} ,g1/1/1-{module_access_ports}\r"
            interface_uplink = f"interface range te1/1/1-{uplink_ports}\r"

    # Configure non stacking switches with fixed uplinks.
    elif (stackingSwitch == False) and fixedUplink:
        if tenGigAccess == 0 and tenGigUplink == 0:
            access_ports = (oneGigAccess + (oneGigUplink - 1))
            uplink_port = (access_ports + 1)
            # Generate the interface range command for non stacking switches
            interface_access = f"interface range g0/1-{access_ports}\r"
            interface_uplink = f"interface g0/{uplink_port}\r"
        elif tenGigAccess == 0 and tenGigUplink > 0:
            access_ports = (oneGigAccess + (oneGigUplink))
            uplink_ports = tenGigUplink
            # Generate the interface range command for non stacking switches
            interface_range_access = f"interface range g0/1-{access_ports}\r"
            interface_uplink = f"interface range te0/1-{uplink_ports}\r"
    
    # Configure non stacking switches with modular uplinks.
    elif stackingSwitch == False and modularUplink:
        # Configure gigabit non stacking switches with no module installed.
        if installedUplinkMod1 == "none":
            access_ports == (oneGigAccess - 1)
            uplink_port == (oneGigAccess)
            
            # Generate the interface range command for non stacking switches with no uplinks.
            interface_access = f"interface range g0/1-{access_ports}\r"
            interface_uplink = f"interface g1/{uplink_port}\r"
        
        # Configure gigabit non stacking switches with gigabit module installed.
        if tenGigAccess == 0 and tenGigPorts == 0:
            access_ports = (oneGigAccess)
            module_access_ports = (oneGigPorts - 1)
            uplink_port = (oneGigPorts)
           
            # Generate the interface range command for non stacking switches with gigabit module installed.
            interface_access = f"interface range g0/1-{access_ports} ,g1/1-{module_access_ports}\r"
            interface_uplink = f"interface g1/{uplink_port}\r"
        
        # Configure gigabit non stacking switches with gigabit/10 gig module installed.
        elif tenGigAccess == 0 and (0 < tenGigPorts < 4):
            access_ports = (oneGigAccess)
            module_access_ports = (oneGigPorts)
            uplink_ports = tenGigPorts
            
            # Generate the interface range command for stacking switches
            interface_access = f"interface range g0/1-{access_ports} ,g1/1-{module_access_ports}\r"
            interface_uplink = f"interface range te0/1-{uplink_ports}\r"


    if userMode != "globalConfig":
        enterConfigMode()
    
    # Configure Management Port
    if OOBE == True:
        sendCMD(interface_OOBE)
        sendCMD("ip address 10.1.8.20 255.255.255.0\r")
        sendCMD("no shut\r")

    # Configure Access Ports
    sendCMD(interface_access)
    sendCMD("switchport mode access\r")
    sendCMD("switchport access vlan 10\r")
    sendCMD("span portf\r")

    # Configure Uplink Ports
    sendCMD(interface_uplink)
    outputProc()
    if multiLayer and ("3850" not in switchModel and "3650" not in switchModel):
        sendCMD("swi tru en do\r")
    sendCMD("swi mo tru\r")
    sendCMD("swi tru nat vlan 108\r")
    sendCMD("end\r")
    userMode = "privExec"


def config_errdisable(debug):
    debugMode(debug)
    global userMode
    if userMode != "globalConfig":
        enterConfigMode()

    sendCMD("service internal\r")
    sendCMD("no errdisable detect cause gbic-invalid\r")
    sendCMD("errdisable recovery cause udld\r")
    sendCMD("errdisable recovery cause bpduguard\r")
    sendCMD("errdisable recovery cause security-violation\r")
    sendCMD("errdisable recovery cause pagp-flap\r")
    sendCMD("errdisable recovery cause dtp-flap\r")
    sendCMD("errdisable recovery cause link-flap\r")
    sendCMD("errdisable recovery cause sfp-config-mismatch\r")
    sendCMD("errdisable recovery cause gbic-invalid\r")
    sendCMD("errdisable recovery cause l2ptguard\r")
    sendCMD("errdisable recovery cause psecure-violationv")
    sendCMD("errdisable recovery cause port-mode-failure\r")
    sendCMD("errdisable recovery cause dhcp-rate-limit\r")
    sendCMD("errdisable recovery cause pppoe-ia-rate-limit\r")
    sendCMD("errdisable recovery cause mac-limit\r")
    sendCMD("errdisable recovery cause storm-control\r")
    sendCMD("errdisable recovery cause inline-power\r")
    sendCMD("errdisable recovery cause arp-inspection\r")
    sendCMD("errdisable recovery cause loopback\r")
    sendCMD("errdisable recovery cause psp\r")
    sendCMD("errdisable recovery interval 30\r")
    sendCMD("service unsupported-transceiver\r")
    sendCMD("end\r")
    userMode = "privExec"

def debugMode(debug):
    if debug:
        # Debug Break point
        frame = inspect.currentframe().f_back
        function_name = frame.f_code.co_name
        print(f"\rDebug: called from {function_name}")
        input("Press Enter to continue: ")

def specTagInfo(debug):
    debugMode(debug)
    print("\nSwitch Information\nSpecs and Features:")
    print("Switch Model: ", specTagModel)
    print("Switch OS Image: ", switchIOS )
    if int(oneGigAccess) > 0:
        print("1 Gig Access Ports: ", oneGigAccess)
    if tenGigAccess > 0:
        print("10 Gig Access Ports: ", tenGigAccess)
    if oneGigUplink > 0:
        print("1 Gig Uplink Ports: ", oneGigUplink)
    if tenGigUplink > 0:
        print("10 Gig Uplink Ports: ", tenGigUplink)
    if tenGigX2 > 0:
            print("10 Gig X2 Ports: 2")
    if OOBE:
        print("OOBE")
        print("OOBE Speed: ", OOBE_Speed)
    if modularStacking:
        print("Modular Stacking")
    if fixedStacking:
        print("Fixed Stacking")
    if modularUplink:
        print("Modular Uplink")
    if fixedUplink:
        print("Fixed Uplink")
    if multiLayer:
        print("Multi-Layer")
    if powerOverEthernet:
        print("PoE")
    print("Memory: ", Memory)
    print("Storage: ", Storage)
    if externalPower:
        print("External Power")
    if redundantPower:
        print("Redundant Power")
    print("Management: ", management)
    print("USB: ", usb)
    print("Base Price: ", baseprice)
    if modularSwitch:
        print("\rModule Information")
        if modularStacking:
            print("Installed Stack Module: ", installedStackMod)
            print("Module Type: ", moduleType)
            print("For Series: ", forSeries)
            print("Stack Ports: ", str(stackPorts))
            print("Module Price: ", modulePrice)
        if modularUplink:
            if uplinkX2 == False:
                print("Installed Uplink Module: ", installedUplinkMod1)
                print("Module Type: ", moduleType)
                print("For Series: ", forSeries)
                if oneGigPorts > 0:
                    print("1 Gig Ports: ", str(oneGigPorts))
                if tenGigPorts > 0:
                    print("10 Gig Ports: ", str(tenGigPorts))
                print("Module Price: ", modulePrice)

def clearConfigReload(debug):
    debugMode(debug)
    # clear any configs
    sendCMD("wr er\r\r")
    # delete vlan.dat
    sendCMD("delete vlan.dat\r\r\r")
    sendCMD("reload\rno\r\r")

def closeConnection(debug):
    debugMode(debug)
    # Close the connection
    channel.close()
    print("Connection Closed")


def main(host, port, username, password,sshkey, no_config, debug):
    initialConnection(host, port, username, password,sshkey, debug)
    waitForBoot(debug)
    collectSwitchInfo(debug)
    if modularSwitch:
        collectModuleInfo(debug)
    if no_config == False:
        commonSwitchConfig(debug)
        configure_switch(debug)
        config_errdisable(debug)
    specTagInfo(debug)
    if ask_yes_no("Would you like to clear configurations and reload? [y/N]"):
        if userMode == "privExec":
            clearConfigReload(debug)
        elif userMode == "userExec":
            sendCMD("enable\r")
            outputProc()
            clearConfigReload(debug)
        else:
            # return to priv exec mode
            sendCMD("\rend\r")
            outputProc()
            clearConfigReload(debug)
            
    closeConnection(debug)


if __name__ == '__main__':
    args = parse_arguments()
    main(args.host, args.port, args.username, args.password,args.sshkey, args.no_config, args.debug)