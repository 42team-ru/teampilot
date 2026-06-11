#!/bin/bash
set -e
# Start PulseAudio daemon (no real audio hardware needed)
pulseaudio --start --exit-idle-time=-1 --disallow-exit 2>/dev/null || true
exec "$@"
