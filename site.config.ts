/* Overwrite default URLs from lakee GitHub repo (for the frontend)
as we are Dockerising our application */

import config from "../ecosystem.config";
const prodEnv = config.apps[0].env;
const devEnv = config.apps[0].devEnv;
const isProd = process.env.NODE_ENV === "production";
const env = isProd ? prodEnv : devEnv;

const HOST_NAME = "host.docker.internal"; // Change this for public server

export const siteConfig = {
  DH_API_URL: `http://${HOST_NAME}:${env.DH_PORT}`,
  SENSOR_API_URL: `http://${HOST_NAME}:${env.SENSOR_PORT}`,
  SENSOR_WS_URL: `ws://${HOST_NAME}:${env.SENSOR_PORT}/ws/`, // make sure to include trailing slash
};

console.log(siteConfig.DH_API_URL);
