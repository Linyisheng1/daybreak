import { apiDelete, apiGet, apiPost } from "./client";
import { buildQuery } from "./query";

export type PocDefinition = {
  id: number;
  name: string;
  description: string;
  severity: string;
  category: string;
  tags: string[];
  command: string;
  raw_content: Record<string, unknown>;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type PocRunStatus = "queued" | "running" | "passed" | "failed" | "error";

export type PocRun = {
  id: number;
  poc_id: number;
  poc_name: string;
  target: string;
  sandbox_container_id: number | null;
  sandbox_container_name: string;
  status: PocRunStatus;
  command: string;
  output: string;
  exit_code: number | null;
  duration_ms: number;
  error: string;
  authorized_scope: string;
  created_by: number;
  started_at: string;
  finished_at: string | null;
};

type Page<T> = {
  page: number;
  size: number;
  total: number;
  items: T[];
};

type CommonResponse<T> = {
  code: number;
  message: string;
  data: T | null;
};

export type RunPocRequest = {
  target: string;
  execution_mode: "direct" | "sandbox";
  sandbox_container_id?: number | null;
  authorized: boolean;
  authorized_scope: string;
  timeout_seconds: number;
};

const POC_PATH = "/api/poc-verifications";

export function queryPocs(params: { page?: number; size?: number; keyword?: string; severity?: string; category?: string }) {
  return apiGet<CommonResponse<Page<PocDefinition>>>(`${POC_PATH}${buildQuery(params)}`);
}

export function importPoc(content: string) {
  return apiPost<CommonResponse<PocDefinition>>(`${POC_PATH}/import`, { content });
}

export function deletePoc(id: number) {
  return apiDelete<CommonResponse<{ id: number }>>(`${POC_PATH}/${id}`);
}

export function runPoc(id: number, payload: RunPocRequest) {
  return apiPost<CommonResponse<PocRun>>(`${POC_PATH}/${id}/run`, payload);
}

export function queryPocRuns(params: { page?: number; size?: number; poc_id?: number }) {
  return apiGet<CommonResponse<Page<PocRun>>>(`${POC_PATH}/runs${buildQuery(params)}`);
}
