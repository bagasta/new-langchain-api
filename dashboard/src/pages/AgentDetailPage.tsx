import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  AgentExecutePayload,
  AgentExecutionRecord,
  AgentResponse,
  executeAgent,
  fetchAgentExecutions,
  getAgent,
} from "../api/agents";
import Loader from "../components/Loader";
import "../styles/agent.css";

dayjs.extend(relativeTime);

type RouteParams = {
  agentId: string;
};

function serialisePayload(payload: unknown) {
  if (!payload) {
    return "-";
  }
  try {
    return JSON.stringify(payload, null, 2);
  } catch (error) {
    console.warn("Failed to stringify payload", error);
    return String(payload);
  }
}

function AgentDetailPage() {
  const navigate = useNavigate();
  const { agentId } = useParams<RouteParams>();
  const [agent, setAgent] = useState<AgentResponse | null>(null);
  const [agentLoading, setAgentLoading] = useState(true);
  const [executions, setExecutions] = useState<AgentExecutionRecord[]>([]);
  const [executionsLoading, setExecutionsLoading] = useState(true);
  const [input, setInput] = useState("");
  const [parameters, setParameters] = useState("{}");
  const [sessionId, setSessionId] = useState("");
  const [lastResponse, setLastResponse] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedParameters = useMemo(() => {
    if (!parameters.trim()) {
      return undefined;
    }
    try {
      return JSON.parse(parameters);
    } catch (err) {
      return undefined;
    }
  }, [parameters]);

  const loadAgent = useCallback(async () => {
    if (!agentId) {
      return;
    }
    setAgentLoading(true);
    try {
      const data = await getAgent(agentId);
      setAgent(data);
    } catch (err) {
      console.error("Failed to load agent", err);
      setError("Agent not found or inaccessible.");
    } finally {
      setAgentLoading(false);
    }
  }, [agentId]);

  const loadExecutions = useCallback(async () => {
    if (!agentId) {
      return;
    }
    setExecutionsLoading(true);
    try {
      const data = await fetchAgentExecutions(agentId);
      setExecutions(data);
    } catch (err) {
      console.error("Failed to load executions", err);
      setError("Unable to fetch execution history.");
    } finally {
      setExecutionsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (!agentId) {
      return;
    }
    void loadAgent();
    void loadExecutions();
  }, [agentId, loadAgent, loadExecutions]);

  const handleExecute = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!agentId) {
        return;
      }
      if (!input.trim()) {
        setError("Please provide input for the agent.");
        return;
      }
      if (parameters.trim() && parsedParameters === undefined) {
        setError("Parameters must be valid JSON.");
        return;
      }

      const payload: AgentExecutePayload = {
        input: input.trim(),
        parameters: parsedParameters,
        session_id: sessionId.trim() || undefined,
      };

      setSubmitting(true);
      setError(null);
      try {
        const response = await executeAgent(agentId, payload);
        setLastResponse(response.response ?? "Agent execution started. Check history for updates.");
        await loadExecutions();
      } catch (err) {
        console.error("Failed to execute agent", err);
        setError("Agent execution failed. Check the agent configuration and try again.");
      } finally {
        setSubmitting(false);
      }
    },
    [agentId, input, loadExecutions, parsedParameters, parameters, sessionId],
  );

  if (!agentId) {
    return (
      <div className="agent-page">
        <div className="panel">
          <p>Missing agent identifier.</p>
          <button type="button" className="secondary" onClick={() => navigate(-1)}>
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="agent-page">
      <div className="breadcrumbs">
        <Link to="/">← Back to dashboard</Link>
      </div>

      {error ? (
        <div className="banner warning">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <section className="panel">
        {agentLoading ? (
          <Loader message="Loading agent details..." />
        ) : agent ? (
          <div className="agent-summary">
            <div>
              <h1>{agent.name}</h1>
              <p className="muted">Status: {agent.status}</p>
            </div>
            <div className="agent-summary-config">
              <div>
                <span className="label">Model</span>
                <strong>{agent.config.llm_model ?? "?"}</strong>
              </div>
              <div>
                <span className="label">Temperature</span>
                <strong>{agent.config.temperature ?? "-"}</strong>
              </div>
              <div>
                <span className="label">Memory</span>
                <strong>{agent.config.memory_type ?? "-"}</strong>
              </div>
              <div>
                <span className="label">Reasoning</span>
                <strong>{agent.config.reasoning_strategy ?? "-"}</strong>
              </div>
            </div>
          </div>
        ) : (
          <p>Agent not found.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Run agent</h2>
        </div>
        <form className="execute-form" onSubmit={handleExecute}>
          <label>
            Prompt
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask the agent to perform a task"
              rows={4}
              required
            />
          </label>
          <div className="execute-form-grid">
            <label>
              Parameters (JSON)
              <textarea
                value={parameters}
                onChange={(event) => setParameters(event.target.value)}
                rows={4}
              />
            </label>
            <label>
              Session ID (optional)
              <input
                type="text"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="Use the same id to continue a conversation"
              />
            </label>
          </div>
          <div className="execute-actions">
            <button type="button" className="secondary" onClick={() => setInput("")}>Reset</button>
            <button type="submit" className="primary" disabled={submitting}>
              {submitting ? "Running..." : "Run agent"}
            </button>
          </div>
        </form>
        {lastResponse ? (
          <div className="execution-result">
            <h3>Latest response</h3>
            <pre>{lastResponse}</pre>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Execution history</h2>
          <button type="button" className="secondary" onClick={() => void loadExecutions()} disabled={executionsLoading}>
            {executionsLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {executionsLoading ? (
          <Loader message="Loading executions..." />
        ) : executions.length ? (
          <div className="execution-table-wrapper">
            <table className="execution-table">
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Status</th>
                  <th>Input</th>
                  <th>Output</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((entry) => (
                  <tr key={entry.id}>
                    <td>{dayjs(entry.created_at).format("YYYY-MM-DD HH:mm")}</td>
                    <td>{entry.status}</td>
                    <td>
                      <pre>{serialisePayload(entry.input)}</pre>
                    </td>
                    <td>
                      <pre>{serialisePayload(entry.output)}</pre>
                    </td>
                    <td>{entry.duration_ms ? `${entry.duration_ms} ms` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No executions recorded for this agent yet.</p>
        )}
      </section>
    </div>
  );
}

export default AgentDetailPage;
