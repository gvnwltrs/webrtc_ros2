import asyncio
import json
from aiohttp import web  # server
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import aiohttp_cors
import logging
import numpy as np  # Make sure numpy is imported for generating dummy frames

pcs = set()  # Peer Connections

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# WebRTC Video Stream Track (example dummy implementation)
class VideoStreamTrackExample(VideoStreamTrack):
    async def recv(self):
        from av import VideoFrame  # Ensure you have PyAV installed (`pip install av`)
        import time
        # Generate a dummy frame (for demonstration)
        frame = VideoFrame.from_ndarray(
            np.zeros((480, 640, 3), dtype=np.uint8), format="bgr24"
        )
        frame.pts = time.time() * 1000000
        frame.time_base = (1, 1000000)
        loger.info(f"Sending frame now... {frame}")
        return frame

def filter_sdp_for_vp8(sdp):
    lines = sdp.splitlines()
    filtered_lines = [line for line in lines if "H264" not in line]
    return "\r\n".join(filtered_lines)

async def offer(request):
    try:
        params = await request.json()
        logger.info(f"Received SDP offer: \n{params['sdp']}")
        logger.info(f"Received SDP type: \n{params['type']}")

        # Test to Create a new RTC Peer Connection
        # Hack
        #if 'm=video' not in params['sdp']:
        #    param['sdp'] += '\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na=sendrecv\r\n' 
        #sdp = params['sdp']
        #sdp = params['sdp'].replace('a=extmap-allow-mixed\r\n', '')
        #offer = RTCSessionDescription(sdp, type=params['type'])

        # Create a new RTC Peer Connection
        offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
        pc = RTCPeerConnection()
        pcs.add(pc)

        # Add a dummy video track (replace with your actual track as needed)
        pc.addTransceiver('video', direction='sendonly')
        pc.addTrack(VideoStreamTrackExample())

        # Set the remote description (received offer)
        await pc.setRemoteDescription(offer)

        # FIXME: 
        # Create and set the local description (answer)
        answer = await pc.createAnswer()

       # answer_sdp = filter_sdp_for_vp8(pc.localDescription.sdp)
       # await pc.setLocalDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))
        
        # FIXME: 
        await pc.setLocalDescription(answer)
        logger.info(f"Generated SDP answer to send: \n{pc.localDescription.sdp}")
        logger.info(f"Created SDP answer: \n{answer.sdp}")

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            ),
        )
    except Exception as e:
        logger.error(f"Error processing offer: \n{str(e)}")
        import traceback
        logger.error(f"{traceback.format_exc()}")

        #return web.Response(status=500, text="Internal Server Error: " + str(e))
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            ),
        )

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

app = web.Application()
app.router.add_post("/offer", offer)
app.on_shutdown.append(on_shutdown)

# CORS configuration
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods=["GET", "POST"]
    )
})
for route in list(app.router.routes()):
    cors.add(route)

web.run_app(app, host="0.0.0.0", port=8080)

