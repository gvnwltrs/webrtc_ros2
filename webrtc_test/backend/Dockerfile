FROM python:3.9-slim

WORKDIR /app


#RUN python --version
#RUN apt-get update && apt-get install -y python3 python3-pip

#RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir aiohttp aiortc aiohttp_cors numpy opencv-python

COPY . .

CMD ["python", "server.py"]

