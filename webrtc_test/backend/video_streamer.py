import asyncio
import aiohttp
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    VideoStreamTrack, 
    RTCIceCandidate, 
    RTCConfiguration,
    RTCIceTransport,
    RTCIceGatherer
)
from av import VideoFrame
import numpy as np
import logging
import re
import traceback

'''
Events to watch:

@pc.on("connectionstatechange")
@pc.on("isconnectionstatechange")
@pc.on("icegatheringstatechange")
@pc.on("signalingstatechange")

'''

logging.basicConfig(level=logging.INFO) # NOTE: Options: [INFO, WARNING, ERROR, CRITICAL (use if you don't want spam)] 
logger = logging.getLogger(__name__)

config = RTCConfiguration(
    iceServers=[]
)

offer_answer_status = {
    "offer_received": False,
    "answer_sent": False,
    "response": {}
}

gathered_ice_candiates_from_answer = {
    "status": "",
    "complete": False
}

class DummyVideoStreamTrack(VideoStreamTrack):
    async def recv(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 2] = 255  # Red frame
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts, video_frame.time_base = self.next_timestamp()
        return video_frame

# FIXME: consolidate these functions into one should be able to convert offer candidates  
# to RTCIceCandidate for remote-candidates and send out local-candidates as serializable JSON
def convert_remote_candidates(candidate_str, sdp_mid="0", sdp_mline_index=0):
    """
    Parse a candidate string into a dictionary for RTCIceCandidate creation.
    
    :param candidate_str: The candidate string to parse.
    :param sdp_mid: The media stream identification (default: "0").
    :param sdp_mline_index: The media line index (default: 0).
    :return: A dictionary with the parsed candidate.
    """
    if candidate_str == '':
        return
    try:
        tokens = candidate_str.split()
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
    except Exception as e:
        logger.error(f"Backend: Error parsing candidate string: {e}")
        traceback.print_exc()

def convert_local_candidates(candidate_str, sdp_mid="0", sdp_mline_index=0):
    """
    Parse a candidate string into a dictionary for RTCIceCandidate creation.
    
    :param candidate_str: The candidate string to parse.
    :param sdp_mid: The media stream identification (default: "0").
    :param sdp_mline_index: The media line index (default: 0).
    :return: A dictionary with the parsed candidate.
    """
    try:
        tokens = candidate_str.split()
        return {
            #"candidate": candidate_str, # Full candidate str
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
    except Exception as e:
        logger.error(f"Backend: Error parsing candidate string: {e}")
        traceback.print_exc()

async def signaling_client():
    global config
    global offer_answer_status
    global gathered_ice_candiates_from_answer
    async with aiohttp.ClientSession() as session:
        pc = RTCPeerConnection(config)
        pc.addTrack(DummyVideoStreamTrack())

        async def checker():
            if offer_answer_status['answer_sent']:
                ...
                #print(f"Backend Checker: remote candidates: {pc.remoteDescription}")

            @pc.on("iceconnectionstatechange")
            def on_iceconnectionstatechange():
                print(f"Backend Checker: ICE connection state: {pc.iceConnectionState}")

            @pc.on("icecandidate")
            async def on_icecandidate(candidate):
                print(f"Backend Checker: ICE Candidate generated: {candidate}")
                await signaling.send(candidate)


        async def fetch_offer():
            if not offer_answer_status['offer_received']:
                response = await session.get("http://localhost:8080/backend/offer")
                if response.status == 200:
                    response = await response.json()
                    logger.info(f"Backend: Offer received from signaling server.")
                    offer_answer_status['offer_received'] = True
                    offer_answer_status['response'] = response

        async def send_answer():
            if not offer_answer_status['answer_sent'] and offer_answer_status['offer_received']:
                data = offer_answer_status['response']
                if not data.get("ice_candidates"):
                    logger.warning("Backend: No ICE candidates received in the offer.")
                    return
                remote_ice_candidates_to_process = data["ice_candidates"]

                '''
                logger.info(
                        f"Backend: Remote ICE candidates are: {remote_ice_candidates_to_process},"
                        f"of type: {type(remote_ice_candidates_to_process[0])}"
                )
                '''

                logger.info("Backend: Now processing remote ICE candidates...")
                converted_remote_ice_candidates = list(
                        map(lambda c: convert_remote_candidates(c["candidate"]),
                            remote_ice_candidates_to_process) 
                )
                remote_ice_candidates = list(filter(None, converted_remote_ice_candidates))
                logger.info(f"Backend: Remote ICE candidates successfully processed: {remote_ice_candidates},"
                )

                offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
                logger.info(f"Backend: Accesssing Offer SDP...")
                await pc.setRemoteDescription(offer)
                logger.info(f"Backend: Offer added to RemoteDescription.")

                ''' 
                    Now add RTCIceCandidate object to ice_candidate so we can connect with the peer 
                    making the offer.
                '''
                # FIXME: delete after testing
                #await pc.addIceCandidate(modified_candidate)
                logger.info(f"Backend: Now Adding Remote ICE candidates...")
                for candidate in remote_ice_candidates:
                    await pc.addIceCandidate(candidate)
                    logger.info(f"Backend: Successfully added ICE candidate: {candidate}")
                logger.info(f"Backend: Successfully added all ICE candidates")

                # Collect ICE candidates generated by the backend
                ice_complete = asyncio.Event()
                @pc.on("icegatheringstatechange")
                async def on_ice_gathering_state_change():
                    logger.info(f"Backend: Checking ICE Gathering state changed: {pc.iceGatheringState}")
                    if pc.iceGatheringState == "complete":
                        ice_complete.set()

                answer = await pc.createAnswer()
                logger.info(f"Backend: Generated Answer SDP.")
                await pc.setLocalDescription(answer)

                # Wait for ICE gathering to complete
                await ice_complete.wait()

                # Extract ICE candidates from the SDP
                backend_ice_candidates = []
                if pc.localDescription and pc.localDescription.sdp:
                    backend_ice_candidates = [
                        line 
                        for line in pc.localDescription.sdp.splitlines() 
                        if line.startswith("a=candidate")
                    ]
                    logger.info(f"Backend: Final ICE Candidates: {backend_ice_candidates}")
                else:
                    logger.warning("Backend: No ICE candidates found in the SDP.")
                    backend_ice_candidates = []

                # DONE: Strip backend ice candidates of "a="
                backend_ice_candidates = [line[2:] for line in backend_ice_candidates]
                logger.info(f"Backend: Formatted ICE Candidates: {backend_ice_candidates}")
                backend_ice_candidates = [
                    convert_local_candidates(candidate) 
                    for candidate in backend_ice_candidates
                ]
                logger.info(f"Backend: ICE Candidates prepped for frontend: {backend_ice_candidates}")

                await session.post("http://localhost:8080/backend/answer", json={
                    "answer": { "sdp": pc.localDescription.sdp, "type": pc.localDescription.type },
                    "ice_candidates": backend_ice_candidates # Send back the ice candidates generated for the answer 
                })
                logger.info("Backend: Answer sent to signaling server.")
                offer_answer_status['answer_sent'] = True

        while True:
            try:
                await fetch_offer()
                await send_answer()
                await checker()
            except Exception as e:
                logger.error(f"Backend: Error fetching or sending data: {e}")
                traceback.print_exc()
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(signaling_client())

