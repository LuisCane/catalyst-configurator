#!/usr/bin/env python3

import argparse, configparser, inspect, json, os, re, socket, telnetlib

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

def initialConnection(host, port):
    # Connect to the AS
    global tn
    try:
        tn = telnetlib.Telnet(host, port)
    except:
        print(f"Connection Refused on Port {port}.")
        exit()

def readPrintOutput(tn, expectedOutput, timeoutSec):
    try:
        output = tn.read_until(expectedOutput, timeout=timeoutSec).decode("ascii")
        print(output)
        return output
    except socket.timeout:
        print(f"Timeout waiting for expected output: {expectedOutput}")
        return ""



def waitForBoot():
    debugMode()
    # Wait for Boot sequence.
    output = tn.read_until(b"Passed", timeout=5).decode("ascii")
    try:
        print(output.decode("ascii"))
    except:
        print(output)
    prev_output = output
    same_count = 0
    while same_count < 30:
        output = tn.read_until(b"Passed", timeout=5).decode("ascii")
        tn.write(b"\r")
        configDialoguePrompt = "Would you like to enter the initial configuration dialog? [yes/no]:"
        try:
            if configDialoguePrompt in output:
                same_count = 31
                tn.write(b"n\r")
            elif "Switch>" in output:
                same_count = 31
            elif "Switch#" in output:
                same_count = 31
            elif "Switch(config)#" in output:
                tn.write(b"end\r")
                same_count = 31
            else:
                print(output.decode("ascii"))
                print("Waiting for boot sequence..." + str(same_count) + "/30")
        except:
            if configDialoguePrompt in output:
                same_count = 31
                tn.write(b"n\r")
            elif "Switch>" in output:
                same_count = 31
            elif "Switch#" in output:
                same_count = 31
            elif "Switch(config)#" in output:
                tn.write(b"end\r")
                same_count = 31
            else:
                print(output)
                print("Waiting for boot sequence..." + str(same_count) + "/30")
        if output == prev_output:
            same_count += 1
        else:
            prev_output = output
            same_count = 0
    # Send a carriage return signal
    global userMode
    tn.write(b"\r")
    # Read the output and print it to the console
    output = tn.read_until(b"Switch>", timeout=2)
    if "Switch>" in output.decode("ascii"):
        print(output.decode("ascii"))
        userMode = "userExec"
    elif "Switch#" in output.decode("ascii"):
        print(output.decode("ascii"))
        userMode = "privExec"
    elif "Switch(config)#" in output.decode("ascii"):
        print(output.decode("ascii"))
        tn.write(b"end\r")
        userMode = "userExec"
    else:
        print(output.decode("ascii"))
        print("Check Prompt")
        input("Press Enter to Continue.")
    print("User mode is: ", userMode)

def getSwitchModel():
    debugMode()
    global switchModel
    # Enter show version command and advance through the pages
    tn.write(b"show version\r")
    output = readPrintOutput(tn, b" --More-- ", 1)
    tn.write(b" ")
    output += readPrintOutput(tn, b" --More-- ", 1)
    tn.write(b" ")
    output += readPrintOutput(tn, b"Switch>", 1)
    tn.write(b" \r")
    output += readPrintOutput(tn, b"Switch>", 1)
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

def getSwitchIOS():
    debugMode()
    global switchIOS
    # Enter show version command and advance through the pages
    tn.write(b"show version\r")
    output = readPrintOutput(tn, b" --More-- ", 1)
    tn.write(b" ")
    output += readPrintOutput(tn, b" --More-- ", 1)
    tn.write(b" ")
    output += readPrintOutput(tn, b"Switch>", 1)
    tn.write(b" \r")
    output += readPrintOutput(tn, b"Switch>", 1)
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

def getSwitchInventory():
    debugMode()
    tn.write(b"show inventory\r")
    output = readPrintOutput(tn, b" --more-- ", 2)
    tn.write(b" ")
    output += readPrintOutput(tn, b" --more-- ", 2)
    tn.write(b"\r")
    output += readPrintOutput(tn, b"Swtich>", 1)
    return output

def collectSwitchInfo():
    debugMode()
    global switchModel
    switchModel = getSwitchModel()
    global switchIOS
    switchIOS = getSwitchIOS()
    debugMode()
    attributesSwitch = get_switch_attributes(switchModel)
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

def collectModuleInfo():
    debugMode()
    global installedUplinkMod1
    installedUplinkMod1 = "none"
    global installedUplinkMod2
    installedUplinkMod2 = "none"
    global uplinkX2
    uplinkX2 = False
    global tenGigX2
    tenGigX2 = 0
    if "3750E" in switchModel or "3560E" in switchModel:
        uplinkX2 = True
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
        switchInventory = getSwitchInventory()
        print(switchInventory)
        installedUplinkMod1 = input("If a module is installed, enter the model here or press Enter for none: ").strip()
        if installedUplinkMod1 in [""]:
            installedUplinkMod1 = "none"
        else:
            attributesModule = get_module_attributes(installedUplinkMod1)
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
                oneGigPorts += attributesModule.get('oneGigPorts')
                tenGigPorts += attributesModule.get('tenGigPorts')
    if modularStacking:
        print("Switch has Modular Stacking Feature.")
        switchInventory = getSwitchInventory()
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
        tn.write(b"enable\r")
        readPrintOutput(tn, b"Switch#", 1)
        userMode = "privExec"
        tn.write(b"config terminal\r")
        readPrintOutput(tn, b"Switch(config)#", 1)
        userMode = "globalConfig"
    elif userMode == "privExec":
        # Enter global config mode
        if userMode == "privExec":
            tn.write(b"configure terminal\r")
            readPrintOutput(tn, b"Switch(config)#", 1)
            userMode = "globalConfig"
    else:
        print("Check User Mode")
        input("Press Enter to continue.")

def commonSwitchConfig():
    if userMode != "globalConfig":
        enterConfigMode()
    # Set line console to logging synchronous
    tn.write(b"line con 0\r")
    readPrintOutput(tn, b"Switch(config-line)#", 1)   
    tn.write(b"logg sync\r")
    readPrintOutput(tn, b"Switch(config-line)#", 1)
    tn.write(b"exit\r")
    # Create Vlans
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"vlan 10\r")
    readPrintOutput(tn, b"Switch(config-vlan)#", 1)
    tn.write(b"vlan 108\r")
    readPrintOutput(tn, b"Switch(config-vlan)#", 1)
    tn.write(b"exit\r")
    readPrintOutput(tn, b"Switch(config)#", 1)

def configure_switch():
    debugMode()
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
        tn.write(interface_OOBE.encode("ascii"))
        readPrintOutput(tn, b"Switch(config-if)#", 1)
        tn.write(b"ip address 10.1.8.20 255.255.255.0\r")
        readPrintOutput(tn, b"Switch(config-if)#", 1)
        tn.write(b"no shut\r")
        readPrintOutput(tn, b"Switch(config-if)#", 1)

    # Configure Access Ports
    tn.write(interface_access.encode("ascii"))
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"switchport mode access\r")
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"switchport access vlan 10\r")
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"span portf\r")
    readPrintOutput(tn, b"Switch(config-if)#", 1)

    # Configure Uplink Ports
    tn.write(interface_uplink.encode("ascii"))
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    if multiLayer and ("3850" not in switchModel and "3650" not in switchModel):
        tn.write(b"swi tru en do\r")
        readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"swi mo tru\r")
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"swi tru nat vlan 108\r")
    readPrintOutput(tn, b"Switch(config-if)#", 1)
    tn.write(b"end\r")
    readPrintOutput(tn, b"Switch#", 1)
    userMode = "privExec"


def config_errdisable():
    global userMode
    if userMode != "globalConfig":
        enterConfigMode()

    tn.write(b"service internal\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"no errdisable detect cause gbic-invalid\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause udld\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause bpduguard\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause security-violation\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause pagp-flap\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause dtp-flap\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause link-flap\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause sfp-config-mismatch\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause gbic-invalid\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause l2ptguard\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause psecure-violation\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause port-mode-failure\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause dhcp-rate-limit\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause pppoe-ia-rate-limit\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause mac-limit\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause storm-control\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause inline-power\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause arp-inspection\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause loopback\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery cause psp\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"errdisable recovery interval 30\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"service unsupported-transceiver\r")
    readPrintOutput(tn, b"Switch(config)#", 1)
    tn.write(b"end\r")
    readPrintOutput(tn, b"Switch#", 1)
    userMode = "privExec"

def debugMode():
    debugModeOn = args.debug
    #debugMode = True
    if debugModeOn:
        # Debug Break point
        frame = inspect.currentframe().f_back
        function_name = frame.f_code.co_name
        print(f"\nDebug: called from {function_name}")
        input("Press Enter to continue: ")

def specTagInfo():
    debugMode()
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
    if uplinkX2:
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
        print("\nModule Information\n")
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

def clearConfigReload():
    # clear any configs
    tn.write(b"wr er\r\r")
    readPrintOutput(tn, b"Switch#", 1)
    # delete vlan.dat
    tn.write(b"delete vlan.dat\r\r\r")
    readPrintOutput(tn, b"Switch#", 1)
    tn.write(b"reload\rno\r\r")
    readPrintOutput(tn, b"Switch#", 1)

def closeConnection():
    # Close the connection
    tn.close()
    print("Connection Closed")


def main():
    initialConnection(args.host, args.port)
    waitForBoot()
    collectSwitchInfo()
    if modularSwitch:
        collectModuleInfo()
    configMode = args.no_config
    if configMode == False:
        commonSwitchConfig()
        configure_switch()
        config_errdisable()
    specTagInfo()
    if ask_yes_no("Would you like to clear configurations and reload? [y/N]"):
        if userMode == "privExec":
            clearConfigReload()
        elif userMode == "userExec":
            tn.write(b"enable\r")
            readPrintOutput(tn, b"Switch#", 1)
            clearConfigReload()
        else:
            # return to priv exec mode
            tn.write(b"\rend\r")
            readPrintOutput(tn, b"Switch#", 1)
            clearConfigReload()
            
    closeConnection()


if __name__ == '__main__':
    try:
        with open('config.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(script_dir, 'config.json')) as f:
                config = json.load(f)
        except FileNotFoundError:
            try:
                home_dir = os.path.expanduser('~')
                with open(os.path.join(home_dir, '.bin', 'catalyst-configurator', 'config.json')) as f:
                    config = json.load(f)
            except FileNotFoundError:
                with open('/opt/catalyst-configurator/config.json') as f:
                    config = json.load(f)

    parser = argparse.ArgumentParser(description='Configure Cisco Catalyst Switches via Telnet and print Specs.')
    parser.add_argument('--host', dest='host', default=config['default']['host'],
                        help='the hostname or IP address to connect to')
    parser.add_argument('--port', dest='port', type=int, default=config['default']['port'],
                        help='the TCP port to connect to')
    parser.add_argument('--no-config', action='store_true', default=config['default']['config'],
                        help='Skip Switch Config.')
    parser.add_argument('--debug', action='store_true', default=config['default']['debug'],
                        help='Enable Debugging mode.')
    args = parser.parse_args()
    
    main()
