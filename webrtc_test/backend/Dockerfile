FROM python:3.9-slim

WORKDIR /app


#RUN python --version
#RUN apt-get update && apt-get install -y python3 python3-pip

#RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    iputils-ping \
    avahi-daemon \
    avahi-discover \
    avahi-utils \
    libnss-mdns \
    mdns-scan \
    dbus \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir aiohttp aiortc aiohttp_cors numpy opencv-python av zeroconf pillow

# Enable and start the Avahi daemon
RUN mkdir -p /var/run/dbus /var/run/avahi-daemon

# Modify Avahi configuration to use a custom port (5354)
RUN sed -i 's/^#port=.*/port=5354/' /etc/avahi/avahi-daemon.conf

COPY . .

#CMD ["python", "server.py"]
#CMD python server.py & python video_streamer.py
CMD ["python", "/app/video_streamer.py"]


