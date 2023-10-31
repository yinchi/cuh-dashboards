/* Overwrite default URLs from lakee GitHub repo (for the frontend)
as we are Dockerising our application */

import config from "../ecosystem.config";
const prodEnv = config.apps[0].env;
const devEnv = config.apps[0].devEnv;
const isProd = process.env.NODE_ENV === "production";
const env = isProd ? prodEnv : devEnv;

const HOST_NAME = "host.docker.internal"; // Change this for public server
const VM_NAME = "192.168.56.101" // Virtualbox default for first VM on host-only network

export const siteConfig = {
  DH_API_URL: `http://${HOST_NAME}:5000`,
  SENSOR_API_URL: `http://${VM_NAME}:8000`,
  SENSOR_WS_URL: `ws://${VM_NAME}:8000/ws/`, // make sure to include trailing slash
};
