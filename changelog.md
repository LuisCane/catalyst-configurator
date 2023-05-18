# Change Log
## 2.1
Changed the way the default settings and arguments work. Arguments are now parsed in a function a the begining of the script with the default settings in the function, making it easier to modify the defaults. Fixed compatibility with certain switches.

## 2.0
Changed script to use SSH instead of Telnet

## 1.6
Changed Default Config function to a default settings dictionary called by the argparser.

## 1.5
Added Default Config Function at the beginning of the script. Changed install path for non-root to .local/bin instead of /bin

## 1.4
Removed Config.json and moved default settings to the python script itself.

## 1.3
Script now presents a warning if a device is not found in the dictionary file and prompts user to update the dictionary file and exits the script.

## 1.2
Adjusted the way function variables and aruments work.
Added user prompts for missing arguments.
Minor bug fixes.

## 1.1.1
Added install.sh script.

## 1.1
Added Change Log
Added rules to handle 3750E and 3570E switches
Added Regex to find IOS XE Model and Software versions.
Changed default config to json format.
Added Debug function

## 1.0
Added rules and logic to handle 3750X switches.

## 0.1
Basic functionality. Read Find model in 3750G switches and configure according to dictionary and rules.
