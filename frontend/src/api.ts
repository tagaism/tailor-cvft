import type { Company, Health, Job, Profile } from "./types";

export const apiOrigin = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 30_000): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  const response = await fetch(path, { ...init, headers, signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  profile: () => request<{ profile: Profile; ready: boolean }>("/api/profile"),
  saveProfile: (profile: Profile) =>
    request<{ profile: Profile; ready: boolean }>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  uploadProfile: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ profile: Profile; ready: boolean; imported: boolean }>(
      "/api/profile/upload",
      { method: "POST", body },
      180_000,
    );
  },
  jobs: (status = "") => {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<{ jobs: Job[]; profile_ready: boolean }>(`/api/jobs${query}`);
  },
  createJob: (payload: Record<string, string>) =>
    request<Job>("/api/jobs", { method: "POST", body: JSON.stringify(payload) }),
  job: (id: number) => request<Job>(`/api/jobs/${id}`),
  saveJob: (id: number, payload: Record<string, string>) =>
    request<Job>(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteJob: (id: number) => request<{ ok: boolean }>(`/api/jobs/${id}`, { method: "DELETE" }),
  refetchJob: (id: number) => request<Job>(`/api/jobs/${id}/refetch`, { method: "POST" }),
  buildJob: (id: number) => request<Job>(`/api/jobs/${id}/build`, { method: "POST" }, 600_000),
  companies: () => request<{ companies: Company[] }>("/api/companies"),
  createCompany: (payload: Record<string, string>) =>
    request<Company>("/api/companies", { method: "POST", body: JSON.stringify(payload) }),
  company: (id: number) => request<Company>(`/api/companies/${id}`),
  saveCompany: (id: number, payload: Record<string, string>) =>
    request<Company>(`/api/companies/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteCompany: (id: number) => request<{ ok: boolean }>(`/api/companies/${id}`, { method: "DELETE" }),
};
