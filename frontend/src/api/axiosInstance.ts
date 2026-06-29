import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8888",
  timeout: 35000,
});
