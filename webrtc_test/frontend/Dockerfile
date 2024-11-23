#FROM node:alpine
#FROM node:slim
FROM node:bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y \
    iputils-ping \
    curl \
    avahi-daemon \
    avahi-discover \
    avahi-utils \
    libnss-mdns \
    mdns-scan \
    dbus \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Enable and start the Avahi daemon
RUN mkdir -p /var/run/dbus /var/run/avahi-daemon

RUN npm install -g http-server

COPY . .

CMD ["sh", "-c", "service dbus start && service avahi-daemon start && http-server -p 3000 -a 0.0.0.0 --cors"]
