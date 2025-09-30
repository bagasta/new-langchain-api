import apiClient from "./client";

export interface AgentConfig {
  llm_model: string;
  temperature: number;
  max_tokens: number;
  memory_type: string;
  reasoning_strategy: string;
  system_prompt?: string | null;
}

export interface AgentPayload {
  name: string;
  tools?: string[];
  config?: AgentConfig;
}

export type AgentConfigMap = Partial<AgentConfig> & Record<string, unknown>;

export interface AgentResponse {
  id: string;
  user_id: string;
  name: string;
  config: AgentConfigMap;
  status: string;
  created_at: string;
  updated_at?: string | null;
  auth_required?: boolean;
  auth_url?: string | null;
  auth_state?: string | null;
}

export interface AgentExecutePayload {
  input: string;
  parameters?: Record<string, unknown>;
  session_id?: string;
}

export interface AgentExecuteResponse {
  execution_id: string;
  status: string;
  message: string;
  response?: string | null;
  session_id?: string | null;
}

export interface AgentExecutionRecord {
  id: string;
  input: unknown;
  output: unknown;
  status: string;
  duration_ms?: number | null;
  error_message?: string | null;
  created_at: string;
}

export interface ExecutionStats {
  total_executions: number;
  completed_executions: number;
  failed_executions: number;
  success_rate: number;
  average_duration_ms: number;
}

const AGENTS_BASE = "/api/v1/agents";

export async function listAgents() {
  const { data } = await apiClient.get<AgentResponse[]>(`${AGENTS_BASE}/`);
  return data;
}

export async function createAgent(payload: AgentPayload) {
  const { data } = await apiClient.post<AgentResponse>(`${AGENTS_BASE}/`, payload);
  return data;
}

export async function getAgent(agentId: string) {
  const { data } = await apiClient.get<AgentResponse>(`${AGENTS_BASE}/${agentId}`);
  return data;
}

export async function updateAgent(agentId: string, payload: Partial<AgentPayload>) {
  const { data } = await apiClient.put<AgentResponse>(`${AGENTS_BASE}/${agentId}`, payload);
  return data;
}

export async function deleteAgent(agentId: string) {
  await apiClient.delete(`${AGENTS_BASE}/${agentId}`);
}

export async function executeAgent(agentId: string, payload: AgentExecutePayload) {
  const { data } = await apiClient.post<AgentExecuteResponse>(
    `${AGENTS_BASE}/${agentId}/execute`,
    payload,
  );
  return data;
}

export async function fetchAgentExecutions(agentId: string) {
  const { data } = await apiClient.get<{ executions: AgentExecutionRecord[] }>(
    `${AGENTS_BASE}/${agentId}/executions`,
  );
  return data.executions;
}

export async function fetchExecutionStats() {
  const { data } = await apiClient.get<ExecutionStats>(`${AGENTS_BASE}/executions/stats`);
  return data;
}
