#!/bin/bash
set -e
# Start PulseAudio daemon (no real audio hardware needed)
pulseaudio --start --exit-idle-time=-1 --disallow-exit 2>/dev/null || true

# Wait for PulseAudio socket to be ready (avoids Chrome connecting before PA is up)
for i in $(seq 1 20); do
    if pactl info >/dev/null 2>&1; then
        break
    fi
    sleep 0.3
done

exec "$@"
