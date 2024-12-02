# webrtc_ros2

## Overview
This is meant to be a light weight solution for standing up your own WebRTC server for ROS2 video streams or other data. 

## Current Status (11-22-2024)
- Test setup is working for both MacOS and Linux docker container environments. 
- Added features to support resolving mDNS IPs from a browser on the host system while running and communicating with frontend and backend containers 
- Needs some refinement in the test setup, but it does at least provide a path for how to setup for ROS2 data streaming 

## How to Use
For right now this is only setup up for testing out WebRTC. Simply clone the repo, jump into the "webrtc_test/" folder then run `docker-compose build` then `docker-compose up`. To access the test video stream go to your browser and type in `locahost:3000`. Within 5 secs or so the test stream should be up from the backend (after the WebRTC negotiation if finished for peer-to-peer connection which is frontend to backend). 

## Caveats
I have not got this working with all browsers yet. Currently Firefox seems to behave the best after disabling mDNS so that it works on a local network when trying to resolve ICE candidates. Also, make sure you turn your VPN off when you run this (spent countless hours troubleshooting that before I got this to work 🤦‍♂️). 

## Disabling mDNS in Firefox
1. Open `about:config`.
2. Set `media.peerconnection.ice.obfuscate_host_addresses` to `false`.

## Tools 
When running the server with both frontend and backend containers up, you can open another browser tab and enter `about:webrtc` to bring up the diagnostics tool while it's connecting or connected. Just make sure you have opened a tab with `locahost:3000` so that the connection/negotiation process has started where the frontend starts communicating to the backend. 

## Upcoming Work 
- Plugging in a ROS2 video stream from an image topic on the backend to stream it. 
