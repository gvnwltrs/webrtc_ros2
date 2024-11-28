#!/bin/bash

# Start TURN server
turnserver --no-auth --listening-port 3478 --realm webrtc.local --cli-password=12345 external-ip=10.0.0.67 \
  relay-ip=10.0.0.67 --verbose &

wait
