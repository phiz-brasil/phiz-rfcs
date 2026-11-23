import type { NextConfig } from "next";

const config: NextConfig = {
  trailingSlash: true,                 // the addresses of the old site end in "/" (/rfc/, /nova/, /comments/)
};

export default config;
