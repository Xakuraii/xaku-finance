import { api } from "@/lib/api/client";
import { DuplicateCandidate, ImportJob, ImportRecord } from "../types";

export async function uploadCsvStatement(
  accountId: string,
  file: File,
  mapping?: Record<string, string>
): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("account_id", accountId);
  formData.append("file", file);
  if (mapping) {
    formData.append("mapping", JSON.stringify(mapping));
  }

  // multipart post
  const res = await fetch("/api/v1/imports/upload/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload CSV statement.");
  }

  return res.json();
}

export async function fetchImportJob(jobId: string): Promise<ImportJob> {
  return api.get<ImportJob>(`/api/v1/imports/${jobId}/`);
}

export async function fetchImportRecords(jobId: string): Promise<ImportRecord[]> {
  const data = await api.get<any>(`/api/v1/imports/${jobId}/records/`);
  if (data && Array.isArray(data.results)) {
    return data.results;
  }
  return Array.isArray(data) ? data : [];
}

export async function resolveCandidate(
  jobId: string,
  candidateId: string,
  decision: "import" | "skip"
): Promise<DuplicateCandidate> {
  return api.post<DuplicateCandidate>(`/api/v1/imports/${jobId}/resolve/`, {
    candidate_id: candidateId,
    decision,
  });
}

export async function commitJob(jobId: string): Promise<ImportJob> {
  return api.post<ImportJob>(`/api/v1/imports/${jobId}/commit/`);
}
