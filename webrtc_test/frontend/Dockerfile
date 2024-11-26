#FROM node:alpine
#FROM node:slim
FROM node:bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y \
    coturn \
    iputils-ping \
    curl \
    dbus \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g http-server

COPY . .

# Expose coturn ports
EXPOSE 3478/udp
EXPOSE 3478/tcp

#CMD ["sh", "-c", "http-server -p 3000 -a 0.0.0.0 --cors"]
CMD ["sh", "-c", "turnserver --no-auth --listening-port 3478 --realm webrtc.local --cli-password=yourpassword & http-server -p 3000 -a 0.0.0.0 --cors"]
