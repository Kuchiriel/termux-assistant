#!/data/data/com.termux/files/usr/bin/bash
set -x

mkdir -p ~/.shortcuts/tasks

model=${1,,}
[[ -z "$model" ]] && model="tinydolphin:1.1b-v2.8-q2_K"

# Function to stop the current LLM
function stop_current_llm() {
    pd sh archlinux -- pgrep -f "ollama run" | xargs -r pd sh archlinux -- kill
}

# Function to start Ollama
function start_ollama() {
    pd sh archlinux -- nohup ollama serve &>/dev/null &
    while ! pd sh archlinux -- pgrep -f "ollama serve" &>/dev/null; do
        sleep 1
    done
}

# Function to check and install necessary packages and start services
function setup_environment() {
    [[ ! -d ~/storage ]] && termux-setup-storage
    
    if ! command -v termux-clipboard-set &>/dev/null; then
        echo "Error: Termux:API not found, installing..."
        pkg i termux-api
        exit 1
    fi
    if [[ -z $(pkg show proot-distro) ]]; then
        pkg install proot-distro -y
        pd install archlinux
        pd sh archlinux -- pacman -Syyu --noconfirm
        pd sh archlinux -- ollama -v &>/dev/null || curl -fsSL https://ollama.com/install.sh | sh
        start_ollama
        pd sh archlinux -- ollama pull "$model"
        pd sh archlinux -- nohup ollama run "$model" &>/dev/null &
    else
        if ! pd sh archlinux -- pgrep ollama &>/dev/null; then
            start_ollama
        fi
        
        current_model=$(pd sh archlinux -- ollama ps | awk 'NR==2 {print $1}')
        if [[ "$current_model" != "$model" ]]; then
            stop_current_llm
            pd sh archlinux -- ollama pull "$model"
            pd sh archlinux -- nohup ollama run "$model" &>/dev/null &
        fi
    fi
}

setup_environment

