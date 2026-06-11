/**
 * Base URL for the backend API. In dev the Vite proxy forwards
 * `/api` and `/s` paths to the FastAPI server, so leaving this
 * empty lets the SPA call the same origin.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
