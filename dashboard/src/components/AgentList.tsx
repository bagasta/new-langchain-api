import { Link, useNavigate } from "react-router-dom";

import { AgentResponse } from "../api/agents";

interface AgentListProps {
  agents: AgentResponse[];
  loading: boolean;
  onDelete: (agentId: string) => Promise<void>;
  onEdit?: (agent: AgentResponse) => void;
  onConnect?: (agent: AgentResponse) => void;
  onAddKnowledge?: (agent: AgentResponse) => void;
}

const TOOL_ICONS: Record<string, string> = {
  gmail: "📧",
  google_calendar: "📅",
  google_sheets: "📊",
  csv: "🗂️",
  json: "🧾",
  file_list: "📂",
};

function resolveTools(agent: AgentResponse): string[] {
  const configTools = (agent.config as { tools?: unknown })?.tools;
  if (Array.isArray(configTools)) {
    return configTools.filter((tool): tool is string => typeof tool === "string");
  }
  const directTools = (agent as AgentResponse & { tools?: unknown }).tools;
  if (Array.isArray(directTools)) {
    return directTools.filter((tool): tool is string => typeof tool === "string");
  }
  return [];
}

function AgentList({
  agents,
  loading,
  onDelete,
  onEdit,
  onConnect,
  onAddKnowledge,
}: AgentListProps) {
  const navigate = useNavigate();

  if (loading) {
    return <p className="muted">Loading agents...</p>;
  }

  if (!agents.length) {
    return <p className="muted">No agents yet. Create one to get started.</p>;
  }

  const confirmDelete = async (agentId: string, agentName: string) => {
    const confirmed = window.confirm(`Delete agent "${agentName}"?`);
    if (!confirmed) {
      return;
    }
    await onDelete(agentId);
  };

  const handleEdit = (agent: AgentResponse) => {
    if (onEdit) {
      onEdit(agent);
      return;
    }
    navigate(`/agents/${agent.id}?mode=edit`);
  };

  const handleConnect = (agent: AgentResponse) => {
    if (!agent.auth_url) {
      return;
    }
    if (onConnect) {
      onConnect(agent);
      return;
    }
    window.open(agent.auth_url, "_blank", "noopener,noreferrer");
  };

  const handleAddKnowledge = (agent: AgentResponse) => {
    if (onAddKnowledge) {
      onAddKnowledge(agent);
      return;
    }
    navigate(`/agents/${agent.id}#knowledge`);
  };

  return (
    <div className="agent-grid">
      {agents.map((agent) => (
        <div key={agent.id} className="agent-card">
          <div className="agent-card-header">
            <div>
              <h3>{agent.name}</h3>
              <p className="agent-status">
                Status: {typeof agent.status === "string" ? agent.status.toLowerCase() : String(agent.status)}
              </p>
            </div>
            <Link to={`/agents/${agent.id}`} className="agent-try">
              Try
            </Link>
          </div>
          <div className="agent-card-body">
            <div className="agent-tools-strip">
              {resolveTools(agent).length ? (
                resolveTools(agent).map((tool) => (
                  <span key={tool} className="agent-tool-icon" title={tool}>
                    {TOOL_ICONS[tool] || "🔧"}
                  </span>
                ))
              ) : (
                <span className="agent-tool-empty">No tools assigned</span>
              )}
            </div>
            {agent.auth_required ? (
              <div className="agent-auth-chip">Google connection required</div>
            ) : null}
          </div>
          <div className="agent-action-bar">
            <button type="button" className="agent-pill" onClick={() => handleEdit(agent)}>
              Edit
            </button>
            <button
              type="button"
              className={`agent-pill${agent.auth_required ? "" : " disabled"}`}
              onClick={() => handleConnect(agent)}
              disabled={!agent.auth_required || !agent.auth_url}
            >
              Connect
            </button>
            <button type="button" className="agent-pill" onClick={() => handleAddKnowledge(agent)}>
              Add Knowledge
            </button>
            <button
              type="button"
              className="agent-pill danger"
              onClick={() => confirmDelete(agent.id, agent.name)}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default AgentList;
