import axios from "axios";
import type { Tokens } from "../types";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const access = localStorage.getItem("seatsync.access");
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;
api.interceptors.response.use(undefined, async (error) => {
  const request = error.config;
  if (error.response?.status !== 401 || request._retried || request.url?.includes("/auth/")) throw error;
  request._retried = true;
  const refresh = localStorage.getItem("seatsync.refresh");
  if (!refresh) throw error;
  refreshPromise ??= axios.post<Tokens>(`${baseURL}/auth/refresh`, { refresh_token: refresh })
    .then(({ data }) => {
      localStorage.setItem("seatsync.access", data.access_token);
      localStorage.setItem("seatsync.refresh", data.refresh_token);
      return data.access_token;
    }).finally(() => { refreshPromise = null; });
  request.headers.Authorization = `Bearer ${await refreshPromise}`;
  return api(request);
});
