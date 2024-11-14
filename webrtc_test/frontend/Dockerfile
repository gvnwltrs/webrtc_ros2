FROM node:alpine

WORKDIR /app

RUN npm install -g http-server

COPY . .

CMD ["http-server", "-p", "3000", "-a", "0.0.0.0"]

