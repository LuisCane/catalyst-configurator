#!/bin/bash

# This is a general-purpose function to ask Yes/No questions in Bash, either
# with or without a default answer. It keeps repeating the question until it
# gets a valid answer.
ask() {
  #printf '\n--> Function: %s <--\n' "${FUNCNAME[0]}"
  # https://djm.me/ask
  local prompt default reply

  while true; do

    if [[ "${2:-}" == "Y" ]]; then
      prompt="[Y/n]"
      default=Y
    elif [[ "${2:-}" == "N" ]]; then
      prompt="[y/N]"
      default=N
    else
      prompt="[y/n]"
      default=
    fi

    # Ask the question (not using "read -p" as it uses stderr not stdout)
    printf '\n'
    printf '%s ' $1 $prompt

    read reply

    # Default?
    if [[ -z "$reply" ]]; then
      reply=${default}
    fi

    # Check if the reply is valid
    case "$reply" in
    Y* | y*) return 0 ;;
    N* | n*) return 1 ;;
    esac

  done
}

#Check if User is Root.
IsRoot() {
    if [[ $EUID = 0 ]]; then
      return 0
      else
      return 1
    fi
}

ScriptDirCheck() {
    DirCheckFile=./.dircheckfile
    if [[ -f "$DirCheckFile" ]]; then
        return 0
    else
        printf '\nThis script is being run from outside its intended directory. Please run this script from its main directory.'
        GoodBye
        exit
    fi
}

installScript() {
    echo "Script requires sudo privilege and will install the following packages:"
    echo "python3.11, paramiko (python ssh module)"
    if ask "Would you like to proceed? Y"; then
        Proceeding
        echo "Installing requisite packages."
        sudo apt install -y python3.11
        python3.11 -m pip install paramiko
        sudo python3.11 -m pip install paramiko
        echo "Copying Files to /opt."
        echo "Creating catalyst-configurator directory in /opt"
        sudo mkdir -p /opt/catalyst-configurator
        if [ -f /opt/catalyst-configurator/catalyst-config.py ]; then
            if ask "/opt/catalyst-configurator/catalyst-config.py already exists, overwrite?"; then
                echo "Copying catalyst-config.py to /opt/catalyst-configurator/"
                sudo cp ./catalyst-config.py /opt/catalyst-configurator/catalyst-config.py
            fi
        else
            echo "Copying catalyst-config.py to /opt/catalyst-configurator/"
            sudo cp ./catalyst-config.py /opt/catalyst-configurator/catalyst-config.py
        fi
        echo "Making catalyst-config.py executable"
        sudo chmod +x /opt/catalyst-configurator/catalyst-config.py
        if [ -f /opt/catalyst-configurator/catalyst-config.py ]; then
            if ask "/opt/catalyst-configurator/device-dict.json already exists, overwrite?"; then
                echo "Copying device-dict.json to /opt/catalyst-configurator/"
                sudo cp ./device-dict.json /opt/catalyst-configurator/device-dict.json
            fi
        else
            echo "Copying device-dict.json to /opt/catalyst-configurator/"
            sudo cp ./device-dict.json /opt/catalyst-configurator/device-dict.json
        fi
        if [ -f /opt/catalyst-configurator/README.md ]; then
            if ask "/opt/catalyst-configurator/README.md already exists, overwrite?"; then
                echo "Copying README.md to /opt/catalyst-configurator/"
                sudo cp ./README.md /opt/catalyst-configurator/README.md
            fi
        else
            echo "Copying README.md to /opt/catalyst-configurator/"
            sudo cp ./README.md /opt/catalyst-configurator/README.md
        fi
        if [ -f /opt/catalyst-configurator/changelog.md ]; then
            if ask "/opt/catalyst-configurator/changelog.md already exists, overwrite?"; then
                echo "Copying changelog.md to /opt/catalyst-configurator/"
                sudo cp ./changelog.md /opt/catalyst-configurator/changelog.md
            fi
        else
            echo "Copying changelog.md to /opt/catalyst-configurator/"
            sudo cp ./changelog.md /opt/catalyst-configurator/changelog.md
        fi
        if [ -f /usr/bin/catalyst-config ]; then
            echo "Creating Symbolic Link to catalyst-config.py in /usr/bin as catalyst-config"
            sudo ln -s /opt/catalyst-configurator/catalyst-config.py /usr/bin/catalyst-config
        else
            echo "Symbolic link to catalyst-config.py already exists."
        fi
    fi
}

#Print Proceeding
Proceeding() {
    printf "\nProceeding\n"
}

#Print Goodbye and exit the script
GoodBye() {
    printf "\nGoodbye.\n"
    exit
}

main() {
    ScriptDirCheck
    installScript
    echo "Installation Completed"
    GoodBye
}
main
