FROM node:alpine

WORKDIR /app

COPY . .

RUN npm install -g http-server

CMD ["http-server", "-p", "3000"]

