#!/data/data/com.termux/files/usr/bin/bash
set -x
source ~/.bashrc
language="pt-br"

function assistant_message_box() {
    messages=("How can I assist you today?" "What can I help you with?" "Tell me what you need." "What's is your need?" "How may I be of service?")
    rand=$(($RANDOM % ${#messages[@]}))
    echo "${messages[$rand]}" | trans -b -s auto -t "$language"
}

title="$(trans -b -s auto -t "$language" "Personal assistant")"
hint="$(assistant_message_box)"

function detect_language() {
    local text="$1"
    trans -b -identify "$text" | awk '{print $1}'
}

function call_toast_and_tts() {
    local text="$1"
    local detected_lang
    detected_lang=$(detect_language "$text")
    if [[ $stream == true ]]; then
        local cleaned_text
        cleaned_text=$(echo "$text" | sed 's/[.,!?;:-]//g')
        termux-tts-speak -l "$detected_lang" "$cleaned_text"
    else
        local response
        response=$(trans -b -s auto -t "$language" "$text")
        termux-toast "$response"
        termux-tts-speak -l "$language" "$response"
    fi
}

function call_llm() {
    local prompt="$1"
    local system_message="You are Dolphin a helpful assistant running in Termux on a Cellphone."
    local chatml_template
    chatml_template=$(
        cat <<EOF
${system_message}
user
${prompt}
assistant
EOF
    )
    local PROMPT
    PROMPT=$(jq -nc --arg model "$model" --arg prompt "$chatml_template" --argjson stream "$stream" '{"model": $model, "prompt": $prompt, "stream": $stream}')
    local endpoint="http://localhost:11434/api/generate"
    local RESPONSE=""
    if [[ "$stream" == true ]]; then
        while IFS= read -r line; do
            CHUNK=$(echo "$line" | jq -r '.response')
            [[ "$CHUNK" == "null" || "$CHUNK" == "" ]] && break
            RESPONSE="$RESPONSE$CHUNK"
            for word in $CHUNK; do
                call_toast_and_tts "$word"
            done
        done < <(curl -s "$endpoint" -d "$PROMPT")
        termux-toast "$RESPONSE"
    else
        RESPONSE=$(curl -s "$endpoint" -d "$PROMPT" | jq -r '.response')
        call_toast_and_tts "$RESPONSE"
    fi
    echo "$RESPONSE"
}

function call_openai() {
    local prompt="$1"
    local stream="$3"
    local PROMPT=$(jq -nc --arg model "gpt-4" --arg prompt "$prompt" --arg max_tokens 200 --argjson stream "$stream" --argjson temperature 0.5 --argjson n 1 --argjson stop 'null' --argjson frequency_penalty 0 --argjson presence_penalty 0 '{"model": $model, "prompt": $prompt, "max_tokens": $max_tokens, "stream": $stream, "temperature": $temperature, "n": $n, "stop": $stop, "frequency_penalty": $frequency_penalty, "presence_penalty": $presence_penalty}')
    local RESPONSE=""

    if [[ "$stream" == true ]]; then
        while IFS= read -r line; do
            CHUNK=$(echo "$line" | jq -r '.choices[].text')
            [[ "$CHUNK" == "null" || "$CHUNK" == "" ]] && break
            RESPONSE="$RESPONSE$CHUNK"
            for word in $CHUNK; do
                call_toast_and_tts "$word"
            done
        done < <(curl -s "$OPENAI_API_ENDPOINT" -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $OPENAI_API_KEY" -d "$PROMPT")
        termux-toast "$RESPONSE"
    else
        RESPONSE=$(curl -s "$OPENAI_API_ENDPOINT" -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $OPENAI_API_KEY" -d "$PROMPT" | jq -r '.choices[].text')
        call_toast_and_tts "$RESPONSE"
    fi
    echo "$RESPONSE"
}

function call_commands() {
    local speech="$1"
    speech=$(trans -b -s auto -t en "$speech")
    local model="$2"
    local stream="$3"

    echo "Speech: $speech, Model: $model, Stream: $stream"

    case "$speech" in
    *flashlight*)
        if [[ "$speech" =~ "on" ]]; then
            termux-torch on
            call_toast_and_tts "Flashlight on"
        else
            termux-torch off
            call_toast_and_tts "Flashlight off"
        fi
        ;;
    *find* | *search*)
        call_llm "$speech" "$model" "$stream"
        ;;
    *volume* | *sound*)
        if [[ "$speech" =~ "up" || "$speech" =~ "raise" ]]; then
            volume=$(termux-volume | jq '.[] | select(.stream == "system") | .volume + 1')
            termux-volume system "$volume"
            call_toast_and_tts "Raising the volume to $volume"
        elif [[ "$speech" =~ "down" || "$speech" =~ "lower" ]]; then
            volume=$(termux-volume | jq '.[] | select(.stream == "system") | .volume - 1')
            termux-volume system "$volume"
            call_toast_and_tts "Lowering the volume to $volume"
        fi
        ;;
    *wifi*)
        if [[ "$speech" =~ "on" ]]; then
            termux-wifi-enable true
            call_toast_and_tts "Enabling Wi-Fi"
        else
            termux-wifi-enable false
            call_toast_and_tts "The Wi-Fi is now off, you may be unable to communicate with the bot API."
        fi
        ;;
    *"list notifications"*)
        notifications=$(termux-notification-list)
        call_toast_and_tts "You have the following notifications: $notifications"
        ;;
    *"remove notification"*)
        id=$(echo "$speech" | sed 's/remove notification //')
        termux-notification-remove "$id"
        call_toast_and_tts "Notification with ID $id has been removed."
        ;;
    *toast*)
        message=$(echo "$speech" | sed 's/toast //')
        termux-toast "$message"
        ;;
    *IP*)
        if [[ "$speech" =~ "local" ]]; then
            call_toast_and_tts "The device local IP address is: $(ifconfig | grep broadcast | awk '{print $2}')"
        elif [[ "$speech" =~ "Global" || "$speech" =~ "valid" ]]; then
            call_toast_and_tts "The device global IP address is: $(wget -qO- -4 ifconfig.co)"
        else
            call_toast_and_tts "The device local IP address is: $(ifconfig | grep broadcast | awk '{print $2}') and the Global IP address is: $(wget -qO- -4 ifconfig.co)"
        fi
        ;;
    *battery*)
        if [[ "$speech" =~ "status" || "$speech" =~ "how much" || "$speech" =~ "level" ]]; then
            status=$(termux-battery-status)
            health=$(echo "$status" | jq -c '.health')
            level=$(echo "$status" | jq -c '.percentage')
            plugged=$(echo "$status" | jq -c '.plugged')
            temperature=$(echo "$status" | jq -c '.temperature')
            call_toast_and_tts "Your battery level is $level percent, and the battery health is $health, the phone is currently $plugged and the temperature is $temperature degrees Celsius"
        fi
        ;;
    *screen* | *brightness* | *bright*)
        if [[ "$speech" =~ "too" || "$speech" =~ "much" || "$speech" =~ "very" ]]; then
            if [[ "$speech" =~ "dark" || "$speech" =~ "black" ]]; then
                call_toast_and_tts "Your screen brightness is now at maximum"
                termux-brightness 255
            else
                call_toast_and_tts "Your screen brightness is now at minimum"
                termux-brightness 0
            fi
        fi
        ;;
    *cell* | *telephony*)
        call_llm "Short describe the cell info $(termux-telephony-cellinfo)" "$model" "$stream"
        ;;
    *copy* | *clipboard*)
        text=$(echo "$speech" | sed 's/copy //')
        termux-clipboard-set "$text"
        call_toast_and_tts "I have copied $text to clipboard"
        ;;
    *"take a photo"* | *"take a picture"*)
        file=$(termux-camera-photo -c 0 --jpeg /sdcard/photo.jpg)
        call_toast_and_tts "I have taken a photo and saved it to $file"
        ;;
    *"show notification"*)
        message=$(echo "$speech" | sed 's/show notification //')
        termux-notification --title "My Personal Assistant" --content "$message"
        call_toast_and_tts "I have shown a notification with message: $message"
        ;;
    *vibrate*)
        termux-vibrate -d 1000
        call_toast_and_tts "I have vibrated the device for 1 second"
        ;;
    *call*)
        number=$(echo "$speech" | sed 's/[a-zA-Z ]*//g')
        termux-telephony-call "$number"
        call_toast_and_tts "I am making a call to $number"
        ;;
    *location*)
        location=$(termux-location)
        if [[ -n "$location" ]]; then
            latitude=$(echo "$location" | jq '.latitude')
            longitude=$(echo "$location" | jq '.longitude')
            accuracy=$(echo "$location" | jq '.accuracy')
            location=$(curl -s "https://nominatim.openstreetmap.org/reverse?lat=$latitude&lon=$longitude&format=json" | jq '.address.road, .address.state, .address.country')
            call_toast_and_tts "Your location is $location, the accuracy for this information is $accuracy"
        else
            call_toast_and_tts "Sorry, I couldn't retrieve your location."
        fi
        ;;
    *play* | *pause* | *next* | *previous*)
        command=""
        if [[ "$speech" =~ "play" ]]; then
            command="play"
        elif [[ "$speech" =~ "pause" ]]; then
            command="pause"
        elif [[ "$speech" =~ "next" ]]; then
            command="next"
        elif [[ "$speech" =~ "previous" ]]; then
            command="previous"
        fi
        termux-media-player "$command"
        call_llm "$command" "$model" "$stream"
        ;;
    *infrared*)
        signal=$(echo "$speech" | sed 's/.*transmit //g')
        termux-infrared-transmit "$signal"
        call_toast_and_tts "Transmitted infrared signal: $signal"
        ;;
    *)
        call_llm "$speech" "$model" "$stream"
        ;;
    esac
}

model=${2,,}
[[ -z "$2" ]] && model="tinydolphin:latest"
stream=${3,,}
[[ -z "$3" ]] && stream=false
speech="$1"

if [[ -n "$1" ]]; then
    call_commands "$speech" "$model" "$stream"
else
    call_commands "$speech" "$model" "$stream"
    termux-tts-speak "$hint"
    speech=$(termux-dialog speech -i "$hint" -t "$title" | jq '.text')
fi
