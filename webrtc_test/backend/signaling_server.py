from aiohttp import web
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

offer_answer_status = {
    "offer_received": False,
    "offer_sent": False,
    "answer_received": False,
    "answer_sent": False,
}

state = {
    "frontend_offer": None,
    "frontend_ice_candidates": [],
    "backend_answer": None,
    "backend_ice_candidates": []
}

# <ACTION>: CORS handling middleware
async def cors_middleware(app, handler):
    try:
        logger.info(f"Signaling Server: ===================Handling CORS middleware==================")
        async def middleware_handler(request):
            response = await handler(request)
            if response is None:
                response = Response(status=500, text="Internal Server Error")  # Ensure a valid response is returned
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
    except Exception as e:
        return Response(status=500, text=f"Unhandled Exception: {e}")
    return middleware_handler

# <ACION>: 
async def handle_preflight(request):
    logger.info(f"Signaling Server: ==================Handling preflight=========================")
    return web.Response(status=200)

async def handle_offer(request):
    if not offer_answer_status['offer_received']:
        data = await request.json()
        state["frontend_offer"] = data["offer"]
        state["frontend_ice_candidates"] = data.get("ice_candidates", [])
        logger.info("Signaling Server: Received offer and ICE candidates from frontend.")
        offer_answer_status['offer_received'] = True
        return web.Response(status=200, text="Offer received")

async def send_offer_to_backend(request):
    if not offer_answer_status['offer_sent']:
        if state["frontend_offer"]:
            response = {
                "offer": state["frontend_offer"],
                "ice_candidates": state["frontend_ice_candidates"]
            }
            logger.info("Signaling Server: Sending offer and ICE candidates to backend.")
            offer_answer_status['offer_sent'] = True
            return web.json_response(response)
        return web.Response(status=404, text="No offer available")

async def handle_answer(request):
    if not offer_answer_status['answer_received']:
        data = await request.json()
        state["backend_answer"] = data["answer"]
        state["backend_ice_candidates"] = data.get("ice_candidates", [])
        logger.info("Signaling Server: Received answer and ICE candidates from backend.")
        offer_answer_status['answer_received'] = True
        return web.Response(status=200, text="Answer received")

async def send_answer_to_frontend(request):
    if not offer_answer_status['answer_sent']:
        if state["backend_answer"]:
            response = {
                "answer": state["backend_answer"],
                "ice_candidates": state["backend_ice_candidates"]
            }
            logger.info("Signaling Server: Sending answer and ICE candidates to frontend.")
            offer_answer_status['answer_sent'] = True
            return web.json_response(response)
        return web.Response(status=404, text="No answer available")

app = web.Application()
# Add CORS middleware
app.router.add_options('/{tail:.*}', handle_preflight)  # Handle CORS preflight requests
app.middlewares.append(cors_middleware)

app.router.add_post("/frontend/offer", handle_offer)
app.router.add_get("/backend/offer", send_offer_to_backend)
app.router.add_post("/backend/answer", handle_answer)
app.router.add_get("/frontend/answer", send_answer_to_frontend)

web.run_app(app, port=8080)

