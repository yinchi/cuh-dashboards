FROM node:current-slim
RUN apt update && apt upgrade -y
RUN apt install wget -y
RUN wget https://github.com/lakeesiv/digital-twin/archive/refs/tags/publish.tar.gz
RUN tar -xzf publish.tar.gz
WORKDIR /digital-twin-publish
RUN npm install -g pnpm
RUN pnpm install
COPY site.config.ts web/site.config.ts
RUN pnpm build:web
CMD pnpm start:web
