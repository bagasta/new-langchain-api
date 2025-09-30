import apiClient from "./client";

export interface ToolResponse {
  id: string;
  name: string;
  description?: string | null;
  schema: Record<string, unknown>;
  type: string;
  created_at: string;
}

const TOOLS_BASE = "/api/v1/tools";

export async function listTools(toolType?: string) {
  const params = toolType ? { tool_type: toolType } : undefined;
  const { data } = await apiClient.get<ToolResponse[]>(`${TOOLS_BASE}/`, { params });
  return data;
}

export async function getToolSchema(toolName: string) {
  const { data } = await apiClient.get(`${TOOLS_BASE}/schemas/${toolName}`);
  return data;
}

export interface ToolExecutionRequest {
  tool_id: string;
  parameters: Record<string, unknown>;
}

export async function executeTool(payload: ToolExecutionRequest) {
  const { data } = await apiClient.post(`${TOOLS_BASE}/execute`, payload);
  return data;
}

export async function getRequiredScopes(toolNames: string[]) {
  const { data } = await apiClient.get(`${TOOLS_BASE}/scopes/required`, {
    params: { tools: toolNames.join(",") },
  });
  return data;
}
