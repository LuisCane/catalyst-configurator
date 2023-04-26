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

installAsRoot() {
    echo "Script run as root. Copying Files to /opt"
    if ask "Would you like to proceed? Y"; then
        Proceeding
        echo "Creating catalyst-configurator directory in /opt"
        mkdir -p /opt/catalyst-configurator
        echo "Copying catalyst-config.py to /opt/catalyst-configurator/"
        cp ./catalyst-config.py /opt/catalyst-configurator/catalyst-config.py
        echo "Making catalyst-config.py executable"
        chmod +x /opt/catalyst-configurator/catalyst-config.py
        echo "Copying device-dict.json to /opt/catalyst-configurator/"
        cp ./device-dict.json /opt/catalyst-configurator/device-dict.json
        echo "Copying README.md to /opt/catalyst-configurator/"
        cp ./README.md /opt/catalyst-configurator/README.md
        echo "Copying changelog.md to /opt/catalyst-configurator/"
        cp ./changelog.md /opt/catalyst-configurator/changelog.md
        echo "Creating Symbolic Link to catalyst-config.py in /usr/bin as catalyst-config"
        ln -s /opt/catalyst-configurator/catalyst-config.py /usr/bin/catalyst-config
    fi
}

installAsUser() {
    echo "Script run as root. Copying Files to ~/.local/bin"
    if ask "Would you like to proceed? Y"; then
        Proceeding
        echo "Creating catalyst-configurator directory in ~/.local/bin/"
        mkdir -p ~/.local/bin/catalyst-configurator
        echo "Copying catalyst-config.py to ~/.local/bin/catalyst-configurator/"
        cp ./catalyst-config.py ~/.local/bin/catalyst-configurator/catalyst-config.py
        echo "Making catalyst-config.py executable"
        chmod +x ~/.local/bin/catalyst-configurator/catalyst-config.py
        echo "Copying device-dict.json to ~/.local/bin/catalyst-configurator/"
        cp ./device-dict.json ~/.local/bin/catalyst-configurator/device-dict.json
        echo "Copying README.md to ~/.local/bin/catalyst-configurator/"
        cp ./README.md ~/.local/bin/catalyst-configurator/README.md
        echo "Copying changelog.md to ~/.local/bin/catalyst-configurator/"
        cp ./changelog.md ~/.local/bin/catalyst-configurator/changelog.md
        echo "Creating Symbolic Link to catalyst-config.py ~/.local/bin/catalyst-config"
        ln -s ~/.local/bin/catalyst-config/catalyst-config.py ~/.local/bin/catalyst-config
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

check_exit_status() {
    if [ $? -eq 0 ]; then
        printf '\nSuccess\n'
    else
        printf '\nError\nThe last command exited with an error.\n'
        if ask "Exit script?" N; then
            GoodBye
        else
            Proceeding
        fi
    fi
}

main() {
    ScriptDirCheck
    if IsRoot; then
        installAsRoot
    else
        installAsUser
    fi
    echo "Installation Completed"
    GoodBye
}
main
