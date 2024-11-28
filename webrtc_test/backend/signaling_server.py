from aiohttp import web
from aiohttp.web import Response
import logging
import json
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

offer_answer_status = {
    "offer_received": False,
    "offer_sent": False,
    "answer_received": False,
    "answer_sent": False,
}

state = {
    "backend_offer": None,
    "backend_ice_candidates": [],
    "frontend_answer": None,
    "frontend_ice_candidates": [],
    "trickled_candidates": {"backend": [], "frontend": []}
}

# <ACTION>: CORS handling middleware
@web.middleware
async def cors_middleware(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = web.Response(status=ex.status, text=str(ex))
    except Exception as e:
        response = web.Response(status=500, text=f"Unhandled Exception: {e}")
    finally:
            # Handle missing route and add CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# <ACION>: 
async def handle_preflight(request):
    try:
        return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    })
    except Exception as e:
        logger.error(f"Signaling Server: Error handling preflight: {e}")
        traceback.print_exc()

async def handle_offer(request):
    if not offer_answer_status['offer_received']:
        try:
            data = await request.json()
            state["backend_offer"] = data["offer"]
            state["backend_ice_candidates"] = data.get("ice_candidates", [])
            logger.info("Signaling Server: Received offer and ICE candidates from backend.")
            offer_answer_status['offer_received'] = True
            return web.Response(status=200, text="Offer received")
        except Exception as e:
            logger.error(f"Signaling Server: Error handling offer from backend: {e}")
            traceback.print_exc()

async def handle_answer(request):
    if not offer_answer_status['answer_received']:
        try:
            data = await request.json()
            state["frontend_answer"] = data["answer"]
            state["frontend_ice_candidates"] = data.get("ice_candidates", [])
            logger.info("Signaling Server: Received answer and ICE candidates from frontend.")
            offer_answer_status['answer_received'] = True
            return web.Response(status=200, text="Answer received")
        except Exception as e:
            logger.error(f"Signaling Server: Error handling answer from frontend: {e}")
            traceback.print_exc()

async def send_offer_to_frontend(request):
    if not offer_answer_status['offer_sent']:
        try:
            if state["backend_offer"]:
                response = {
                    "offer": state["backend_offer"],
                    "ice_candidates": state["backend_ice_candidates"]
                }
                logger.info(f"Signaling Server: Sending offer and ICE candidates to frontend: {response}")
                offer_answer_status['offer_sent'] = True
                return web.json_response(response)
            return web.Response(status=404, text="No answer available")
        except Exception as e:
            logger.error(f"Signaling Server: Error sending offer to frontend: {e}")
            traceback.print_exc()
            return web.Response(status=500, text="Internal Service Error")

async def send_answer_to_backend(request):
    if not offer_answer_status['answer_sent']:
        try:
            if state["frontend_answer"]:
                response = {
                    "answer": state["frontend_answer"],
                    "ice_candidates": state["frontend_ice_candidates"]
                }
                logger.info("Signaling Server: Sending answer and ICE candidates to backend.")
                offer_answer_status['answer_sent'] = True
                return web.json_response(response)
            return web.Response(status=404, text="No answer available")
        except Exception as e:
            logger.error(f"Signaling Server: Error sending answer to backend: {e}")
            traceback.print_exc()

async def handle_trickle(request):
    data = await request.json()
    candidate = data.get("candidate")
    origin = data.get("origin")

    if candidate and origin in ["backend", "frontend"]:
        state["trickled_candidates"][origin].append(candidate)
        logger.info(f"Signaling Server: Received trickled ICE candidate from {origin}: {candidate}")

        # Forward the candidate to the other peer
        target = "frontend" if origin == "backend" else "backend"
        await forward_trickled_candidate(target, candidate)

    return web.Response(status=200, text="Trickled candidate handled.")

async def forward_trickled_candidate(target, candidate):
    try:
        url = f"http://{target}:8080/{target}/trickle"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"candidate": candidate})
        logger.info(f"Signaling Server: Forwarded candidate to {target}.")
    except Exception as e:
        logger.error(f"Error forwarding candidate to {target}: {e}")
        traceback.print_exc()

app = web.Application(middlewares=[cors_middleware])
app.router.add_options('/{tail:.*}', handle_preflight)

app.router.add_post("/backend/offer", handle_offer) # backend req
app.router.add_get("/frontend/offer", send_offer_to_frontend) # frontend req
app.router.add_post("/frontend/answer", handle_answer) # frontend req
app.router.add_get("/backend/answer", send_answer_to_backend) # backend req
app.router.add_post("/trickle", handle_trickle)

#web.run_app(app, host="10.0.0.20", port=8080)
web.run_app(app, port=8080)

