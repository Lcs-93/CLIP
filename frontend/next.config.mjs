import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

export default function createNextConfig(phase) {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;

  /** @type {import('next').NextConfig} */
  return {
    reactStrictMode: true,
    // Keep dev artifacts separate from production build artifacts.
    // This prevents chunk/cache conflicts when build and dev run at different times.
    distDir: isDevServer ? ".next-dev" : ".next",
  };
}

