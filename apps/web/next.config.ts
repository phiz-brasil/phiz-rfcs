import type { NextConfig } from "next";

const config: NextConfig = {
  trailingSlash: true,                 // the addresses of the old site end in "/" (/rfc/, /nova/, /comments/)
  async rewrites() {
    return [{ source: "/rfcs/:id(PHZ-\\d{4})/openapi/", destination: "/rfcs/:id/openapi/index.html" }];
  },
};

export default config;
