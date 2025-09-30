import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AgentPayload,
  AgentResponse,
  ExecutionStats,
  createAgent,
  deleteAgent,
  fetchExecutionStats,
  listAgents,
} from "../api/agents";
import { ToolResponse, listTools } from "../api/tools";
import { UserToken, fetchAuthTokens } from "../api/user";
import AgentForm from "../components/AgentForm";
import AgentList from "../components/AgentList";
import Loader from "../components/Loader";
import StatCard from "../components/StatCard";
import TokenList from "../components/TokenList";
import ToolGrid from "../components/ToolGrid";
import TopBar from "../components/TopBar";
import "../styles/dashboard.css";

function formatDuration(ms: number) {
  if (!ms) {
    return "-";
  }
  if (ms < 1000) {
    return `${ms.toFixed(0)} ms`;
  }
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`;
  }
  const minutes = seconds / 60;
  return `${minutes.toFixed(1)} min`;
}

function DashboardLayout() {
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [tools, setTools] = useState<ToolResponse[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [tokens, setTokens] = useState<UserToken[]>([]);
  const [tokensLoading, setTokensLoading] = useState(true);
  const [stats, setStats] = useState<ExecutionStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const handleError = useCallback((message: string, err: unknown) => {
    console.error(message, err);
    setError(message);
  }, []);

  const loadAgents = useCallback(async () => {
    setAgentsLoading(true);
    try {
      const data = await listAgents();
      setAgents(data);
    } catch (err) {
      handleError("Failed to load agents.", err);
    } finally {
      setAgentsLoading(false);
    }
  }, [handleError]);

  const loadTools = useCallback(async () => {
    setToolsLoading(true);
    try {
      const data = await listTools();
      setTools(data);
    } catch (err) {
      handleError("Failed to load tools.", err);
    } finally {
      setToolsLoading(false);
    }
  }, [handleError]);

  const loadTokens = useCallback(async () => {
    setTokensLoading(true);
    try {
      const data = await fetchAuthTokens();
      setTokens(data);
    } catch (err) {
      handleError("Failed to load connected services.", err);
    } finally {
      setTokensLoading(false);
    }
  }, [handleError]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await fetchExecutionStats();
      setStats(data);
    } catch (err) {
      handleError("Failed to load execution statistics.", err);
    } finally {
      setStatsLoading(false);
    }
  }, [handleError]);

  useEffect(() => {
    void loadAgents();
    void loadTools();
    void loadTokens();
    void loadStats();
  }, [loadAgents, loadTools, loadTokens, loadStats]);

  const handleCreateAgent = useCallback(
    async (payload: AgentPayload) => {
      setCreatingAgent(true);
      try {
        const created = await createAgent(payload);
        setAgents((current) => [created, ...current]);
        setShowCreateForm(false);
        await loadStats();
      } catch (err) {
        handleError("Failed to create agent.", err);
        throw err;
      } finally {
        setCreatingAgent(false);
      }
    },
    [handleError, loadStats],
  );

  const handleDeleteAgent = useCallback(
    async (agentId: string) => {
      try {
        await deleteAgent(agentId);
        setAgents((current) => current.filter((agent) => agent.id !== agentId));
        await loadStats();
      } catch (err) {
        handleError("Failed to delete agent.", err);
      }
    },
    [handleError, loadStats],
  );

  const refreshAll = useCallback(async () => {
    setError(null);
    setRefreshing(true);
    await Promise.all([loadAgents(), loadTools(), loadTokens(), loadStats()]);
    setRefreshing(false);
  }, [loadAgents, loadTools, loadTokens, loadStats]);

  const successRate = useMemo(() => {
    if (!stats) {
      return "-";
    }
    const percent = Math.round((stats.success_rate || 0) * 1000) / 10;
    return `${percent}%`;
  }, [stats]);

  const averageDuration = useMemo(() => formatDuration(stats?.average_duration_ms || 0), [stats]);

  return (
    <div className="dashboard-wrapper">
      <TopBar />

      {error ? (
        <div className="banner warning">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="dashboard-actions">
        <button type="button" className="primary" onClick={() => setShowCreateForm(true)}>
          Create agent
        </button>
        <button type="button" className="secondary" onClick={() => void refreshAll()} disabled={refreshing}>
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {showCreateForm ? (
        <div className="panel">
          <div className="panel-header">
            <h2>New agent</h2>
            <button type="button" onClick={() => setShowCreateForm(false)}>
              Close
            </button>
          </div>
          <AgentForm
            availableTools={tools}
            onSubmit={handleCreateAgent}
            onCancel={() => setShowCreateForm(false)}
            submitting={creatingAgent}
          />
        </div>
      ) : null}

      <section className="panel">
        <div className="panel-header">
          <h2>Execution overview</h2>
        </div>
        {statsLoading ? (
          <Loader message="Loading execution metrics..." />
        ) : (
          <div className="stat-grid">
            <StatCard
              label="Total runs"
              value={stats?.total_executions ?? 0}
              helper={`Completed: ${stats?.completed_executions ?? 0}`}
            />
            <StatCard
              label="Success rate"
              value={successRate}
              helper={`Failed: ${stats?.failed_executions ?? 0}`}
            />
            <StatCard label="Avg duration" value={averageDuration} helper="Recent executions" />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Your agents</h2>
        </div>
        <AgentList agents={agents} loading={agentsLoading} onDelete={handleDeleteAgent} />
      </section>

      <section className="panel two-column">
        <div>
          <div className="panel-header">
            <h2>Connected services</h2>
          </div>
          <TokenList tokens={tokens} loading={tokensLoading} />
        </div>
        <div>
          <div className="panel-header">
            <h2>Available tools</h2>
          </div>
          <ToolGrid tools={tools} loading={toolsLoading} />
        </div>
      </section>
    </div>
  );
}

export default DashboardLayout;
