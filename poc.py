#!/usr/bin/env python3

import argparse
import getpass
import inspect
import paramiko

global defaultSettings
defaultSettings = {
        # Default host. String, IP address or Hostname
        "host": "192.168.0.194",
        # Default Port. Integer
        "port": 22,
        # Default Username. String
        "username": "test",
        # Default Password. String
        "password": "password123",
        # Default mode for Debug. Boolean
        "debug": False
    }

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

def initialConnection(host, port, username, password, debug):
    debugMode(debug)
    # Connect to the AS
    global client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout = 10
        )
        print(f"Successfully connected to {host}.")
    except paramiko.BadHostKeyException:
        print(f"Bad Host Key Exception.")
        exit()
    except paramiko.AuthenticationException:
        print(f"Authentication failed when connecting to {host}.")
        exit()
    except:
        print(f"Could not connect to {host}.")
        exit()

def runCMD(command):
    stdin, stdout, stderr = client.exec_command(f'{command}')
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    if error:
        print(f"Error running command '{command}': {error}")
    return output

def debugMode(debug):
    if debug:
        # Debug Break point
        frame = inspect.currentframe().f_back
        function_name = frame.f_code.co_name
        print(f"\nDebug: called from {function_name}")
        input("Press Enter to continue: ")

def getUserFromPasswd ():
    output = runCMD("cat /etc/passwd")
    for line in output.split('\n'):
        fields = line.split(':')
        if len(fields) >= 3 and fields[2] == "1000":
            username = fields[0]
            print(f"The username for user ID 1000 is '{username}'")

def main(host, port, username, password, debug):
    initialConnection(host, port, username, password, debug)
    #runCMD("cat /etc/passwd")
    getUserFromPasswd()
    client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure Cisco Catalyst Switches via Telnet and print Specs.')
    parser.add_argument('--host', dest='host', default=defaultSettings["host"],
                        help='the Hostname or IP address to connect to')
    parser.add_argument('--port', dest='port', type=int, default=defaultSettings["port"],
                        help='the TCP port to connect to')
    parser.add_argument('--username', dest='username', default=defaultSettings["username"],
                        help='the Username for SSH')
    parser.add_argument('--password', dest='password', default=defaultSettings["password"],
                        help='the Password for SSH')
    parser.add_argument('--debug', action='store_true', default=defaultSettings["debug"],
                        help='Enable Debugging mode.')
    args = parser.parse_args()

    # Prompt User for host if none is supplied by arguments or config.json
    if not args.host:
        host = input("Enter host name or IP address: ")
    else:
        host = args.host
    # Prompt User for Port number if none is supplied by arguments or config.json
    if not args.port:
        port = input("Enter port: ")
    else:
        port = args.port
    if not args.username:
        username = input("Enter Username: ")
    else:
        username = args.username
    if not args.password:
        password = getpass.getpass("Enter password: ")
    else:
        password = args.password
    debug = args.debug

    main(host, port, username, password, debug)