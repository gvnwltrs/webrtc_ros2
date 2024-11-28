#!/bin/bash

# Start TURN server
# turnserver --no-auth --listening-port 3478 --realm webrtc.local --cli-password=12345 \
#   --relay-ip 10.0.0.5 --external-ip 10.0.0.5 --listening-ip 10.0.0.5 &
# turnserver --no-auth --listening-port 3478 --realm webrtc.local --cli-password=12345 \
#   --listening-ip 10.0.0.0 &

# Start signaling server
python /app/signaling_server.py &

# Start video streamer
python /app/video_streamer.py &

# Wait for all background processes to finish
wait
