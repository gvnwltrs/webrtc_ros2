import asyncio
import aiohttp
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    VideoStreamTrack, 
    RTCIceServer,
    RTCIceCandidate, 
    RTCConfiguration,
    RTCIceTransport,
    RTCIceGatherer
)
from av import VideoFrame
from PIL import Image
import numpy as np
import logging
import re
import traceback

import hmac
import hashlib
import base64
from datetime import datetime, timedelta

shared_secret = "password"
username = str(int((datetime.utcnow() + timedelta(minutes=10)).timestamp()))
password = base64.b64encode(hmac.new(shared_secret.encode(), username.encode(), hashlib.sha1).digest()).decode()

logging.basicConfig(level=logging.INFO) # NOTE: Options: [INFO, WARNING, ERROR, CRITICAL (use if you don't want spam)] 
logger = logging.getLogger(__name__)

no_server = RTCIceServer(urls=[])
stun_server = RTCIceServer(urls=["stun:10.0.0.67:3478"])
# turn_server = RTCIceServer(urls=["turn:172.20.0.2:3478"], username="dummy")
turn_server = RTCIceServer(urls=["turn:10.0.0.67:3478"], username=username, credential=password)
config = RTCConfiguration(
    iceServers=[stun_server, turn_server]
)
logger.info(f"Backend: ICE configured for: {config}")

offer_answer_status = {
    "offer_sent": False,
    "answer_received": False,
    "response": {}
}

gathered_ice_candiates_from_answer = {
    "status": "",
    "complete": False
}

class DummyVideoStreamTrack(VideoStreamTrack):
    def __init__(self, gif_path):
        super().__init__()
        self.gif_path = gif_path
        self.frames = self._load_gif_frames()
        self.frame_index = 0

    def _load_gif_frames(self):
        """
        Load GIF and convert frames to numpy arrays.
        """
        gif = Image.open(self.gif_path)
        frames = []
        try:
            while True:
                frame = gif.copy().convert("RGB")
                frames.append(np.array(frame))
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass  # End of GIF
        return frames

    async def recv(self):
        """
        Send a single frame from the GIF as a video frame.
        """
        # Get the next frame in the loop
        frame = self.frames[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self.frames)  # Loop GIF

        # Convert the frame to a VideoFrame object
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")

        # Set timestamp
        timestamp = await self.next_timestamp()
        video_frame.pts, video_frame.time_base = timestamp

        return video_frame


async def signaling_client():
    global config
    global offer_answer_status
    global gathered_ice_candiates_from_answer
    global username, password
    backend_ice_candidates = []

    async with aiohttp.ClientSession() as session:
        #signalingUrl ="http://10.0.0.20:8080"
        signalingUrl ="http://localhost:8080"
        pc = RTCPeerConnection(config)
        pc.addTrack(DummyVideoStreamTrack("breakstuff.gif"))

        # Events
        # Store ICE Canddidates when generated
        ice_complete = asyncio.Event()
        @pc.on("icegatheringstatechange")
        async def on_ice_gathering_state_change():
            logger.info(f"Backend: ICE Candidates gathering for offer...")
            if pc.iceGatheringState == "complete":
                ice_complete.set()

        # FIXME: Trickle setup (aiortc issue #499)
        # @pc.on('icegatheringstatechange')
        # def on_icegatheringstatechange():
        #     logging.info('iceGatheringState changed to {}'.format(self.pc.iceGatheringState))
        #     if self.pc.iceGatheringState == 'complete':
        #         # candidates are ready
        #         candidates = self.pc.sctp.transport.transport.iceGatherer.getLocalCandidates()
        #         #add ice candidate iteratively

        # Helpers
        async def wait_for_ice_completion(pc):
            """Wait for ICE gathering to complete."""
            print("Waiting for ICE candidates to be gathered...")
            while pc.iceGatheringState != "complete":
                await asyncio.sleep(0.1)
            print("ICE gathering complete")

        async def send_ice_candidates(session, candidates):
            logger.info(f"Backend: Trickle ICE Candidates starting...")
            for candidate in candidates:
                if candidate:
                    response = await session.post(f"{signalingUrl}/trickle", json={"candidate":candidate});
                    logger.info(f"Backend: Trickle ICE Candidates sent! Response[{response.status}]")
            # response = await session.post(f"{signalingUrl}/trickle", json={candidates});

        def get_generated_ice_candidates(pc) -> list:
            logger.info(f"Backend: Getting generated ICE Candidates ...")
            if pc.localDescription and pc.localDescription.sdp:
                candidates = [
                    line
                    for line in pc.localDescription.sdp.splitlines()
                    if line.startswith("a=candidate")
                ]
                logger.info(f"Backend: Got ICE Candidates!")
                return candidates 

        def format_ice_candidates(candidates) -> list:
            logger.info(f"Backend: Formatting ICE Candidates from local SDP...")
            return [
                line[2:] # strips out "a=" for each candidate
                for line in candidates
            ]

        def convert_ice_candidates_to_send_or_receive(candidate_str, method="send", sdp_mid=0, sdp_mline_index=0):
            if not candidate_str:
                return None
            try:
                tokens = candidate_str.split()
                if method == "send": 
                    return {
                        "candidate": candidate_str, # Full candidate str
                        "component": tokens[1], # RTP "1" or RTCP "2"
                        "foundation": tokens[0].split(":")[1], # Extracte the foundation after "candidate:""
                        "ip": tokens[4], # IP addresses of the candidate
                        "port": int(tokens[5]), # Port number
                        "priority": tokens[3], # Candidate priority
                        "protocol": tokens[2], # Protocol "udp" or "tcp"
                        "type": tokens[7], # Candidate type like "host", "srflx", "relay"
                        "relatedAddress": None, # default
                        "relatedPort": None, # default
                        "sdpMid": sdp_mid, # SDP media ID
                        "sdpMLineIndex": sdp_mline_index, # SDP Media Line Index
                        "tcpType": None
                    }
                elif method == "receive":
                    return RTCIceCandidate ( 
                        component=tokens[1], # RTP "1" or RTCP "2"
                        foundation=tokens[0].split(":")[1], # Extracte the foundation after "candidate:""
                        ip=tokens[4], # IP addresses of the candidate
                        port=int(tokens[5]), # Port number
                        priority=tokens[3], # Candidate priority
                        protocol=tokens[2], # Protocol "udp" or "tcp"
                        type=tokens[7], # Candidate type like "host", "srflx", "relay"
                        relatedAddress=None, # default
                        relatedPort=None, # default
                        sdpMid=sdp_mid, # SDP media ID
                        sdpMLineIndex=sdp_mline_index, # SDP Media Line Index
                        tcpType=None
                    )
                else:
                    logger.error(f"Backend: Check method for parsing candidate string: {e}")
                    return None
            except Exception as e:
                logger.error(f"Backend: Error parsing candidate string: {e}")
                traceback.print_exc()

        def pkg_candidates(candidates) -> list:
            return [
                    convert_ice_candidates_to_send_or_receive(candidate, "send")
                    for candidate in candidates
                ]

        async def set_remote_ice_candidates(pc, candidates):
            for candidate in candidates:
                await pc.addIceCandidate(candidate)
                logger.info(f"Backend: Successfully added ICE candidate: {candidate}")
            logger.info(f"Backend: Successfully added all ICE candidates")

        # Signaling
        async def send_offer():
            if not offer_answer_status['offer_sent']:
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)

                await wait_for_ice_completion(pc)
                await ice_complete.wait()

                candidates = get_generated_ice_candidates(pc)
                candidates = format_ice_candidates(candidates)
                backend_ice_candidates = pkg_candidates(candidates)
                response = await session.post(f"{signalingUrl}/backend/auth", json={
                        "username": username,
                        "password": password
                });
                logger.info(f"Backend: Auth sent: {response}")
                response = await session.post(f"{signalingUrl}/backend/offer", json={
                    "offer": {
                        "sdp": pc.localDescription.sdp,
                        "type": pc.localDescription.type,
                        "username": username,
                        "password": password
                    },
                    "ice_candidates": backend_ice_candidates
                });
                #await send_ice_candidates(session, backend_ice_candidates)

                logger.info(f"Backend: Offer sent: {response}")
                offer_answer_status['offer_sent'] = True

        async def get_answer():
            if offer_answer_status['offer_sent'] and not offer_answer_status['answer_received']:
                response = await session.get(f"{signalingUrl}/backend/answer")
                if response.status == 200:
                    remote_ice_candidates = []
                    response = await response.json()
                    logger.info(f"Backend: Answer received: {response}")
                    answer_data = response["answer"]
                    remote_ice_candidates_data = response["ice_candidates"]


                    # set remote description 
                    answer = RTCSessionDescription(
                        sdp=answer_data["sdp"], type=answer_data["type"]
                    )
                    await pc.setRemoteDescription(answer)

                    # set remote ice canddidates
                    remote_ice_candidates = list(
                            map(lambda c:
                                    convert_ice_candidates_to_send_or_receive(c["candidate"], "receive"),
                                    remote_ice_candidates_data
                                ))
                    logger.info(f"Backend: Candidates from frontend answer: {remote_ice_candidates}")
                    # TODO:Set ice candidates with addIceCandidates

                    offer_answer_status['answer_received'] = True
                else:
                    logger.info(f"Backend: Answer not received from frontend yet..")


        
        while True:
            try:
                await send_offer()
                await get_answer()
            except Exception as e:
                logger.error(f"Backend: Error fetching or sending data: {e}")
                traceback.print_exc()
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(signaling_client())








