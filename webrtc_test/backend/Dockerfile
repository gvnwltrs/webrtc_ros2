FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install aiohttp aiortc aiohttp_cors

CMD ["python", "server.py"]

