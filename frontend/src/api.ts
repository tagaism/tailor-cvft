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

async function buildJobStream(
  id: number,
  style: string,
  onReasoning?: (lines: string[]) => void,
): Promise<Job> {
  const response = await fetch(`/api/jobs/${id}/build?style=${encodeURIComponent(style)}`, {
    method: "POST",
    headers: { Accept: "text/event-stream" },
    signal: AbortSignal.timeout(600_000),
  });
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
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/event-stream")) {
    return (await response.json()) as Job;
  }
  if (!response.body) {
    throw new ApiError("Build stream was empty.", 502);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let job: Job | null = null;
  let streamError = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const dataLine = chunk.split("\n").find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      let payload: { type?: string; lines?: string[]; job?: Job; detail?: string };
      try {
        payload = JSON.parse(dataLine.replace(/^data:\s?/, "")) as typeof payload;
      } catch {
        continue;
      }
      if (payload.type === "reasoning" && Array.isArray(payload.lines)) {
        onReasoning?.(payload.lines);
      } else if (payload.type === "done" && payload.job) {
        job = payload.job;
      } else if (payload.type === "error") {
        streamError = payload.detail || "Build failed.";
      }
    }
  }
  if (streamError) throw new ApiError(streamError, 400);
  if (!job) throw new ApiError("Build finished without a result. Try again.", 502);
  return job;
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
  buildJob: (id: number, style = "times", onReasoning?: (lines: string[]) => void) =>
    buildJobStream(id, style, onReasoning),
  companies: () => request<{ companies: Company[] }>("/api/companies"),
  createCompany: (payload: Record<string, string>) =>
    request<Company>("/api/companies", { method: "POST", body: JSON.stringify(payload) }),
  company: (id: number) => request<Company>(`/api/companies/${id}`),
  saveCompany: (id: number, payload: Record<string, string>) =>
    request<Company>(`/api/companies/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteCompany: (id: number) => request<{ ok: boolean }>(`/api/companies/${id}`, { method: "DELETE" }),
};
