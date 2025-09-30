import { FormEvent, useState } from "react";

import { AgentConfig, AgentPayload } from "../api/agents";
import { ToolResponse } from "../api/tools";

interface AgentFormProps {
  availableTools: ToolResponse[];
  onSubmit: (payload: AgentPayload) => Promise<void>;
  onCancel: () => void;
  submitting: boolean;
}

const defaultConfig: AgentConfig = {
  llm_model: "gpt-3.5-turbo",
  temperature: 0.7,
  max_tokens: 1000,
  memory_type: "buffer",
  reasoning_strategy: "react",
  system_prompt: "",
};

function AgentForm({ availableTools, onSubmit, onCancel, submitting }: AgentFormProps) {
  const [name, setName] = useState("");
  const [tools, setTools] = useState<string[]>([]);
  const [config, setConfig] = useState<AgentConfig>({ ...defaultConfig });
  const [error, setError] = useState<string | null>(null);

  const toggleTool = (toolName: string) => {
    setTools((current) =>
      current.includes(toolName)
        ? current.filter((name) => name !== toolName)
        : [...current, toolName],
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Agent name is required");
      return;
    }

    const trimmedPrompt = config.system_prompt?.trim() || undefined;

    const payload: AgentPayload = {
      name: name.trim(),
      tools,
      config: {
        llm_model: config.llm_model,
        temperature: Number(config.temperature),
        max_tokens: Number(config.max_tokens),
        memory_type: config.memory_type,
        reasoning_strategy: config.reasoning_strategy,
        ...(trimmedPrompt ? { system_prompt: trimmedPrompt } : {}),
      },
    };

    try {
      await onSubmit(payload);
      setName("");
      setTools([]);
      setConfig({ ...defaultConfig });
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Unable to create agent. Please try again.");
    }
  };

  return (
    <form className="agent-form" onSubmit={handleSubmit}>
      <div className="agent-form-grid">
        <label>
          Agent name
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Research assistant"
            required
          />
        </label>
        <label>
          LLM model
          <input
            type="text"
            value={config.llm_model}
            onChange={(event) => setConfig({ ...config, llm_model: event.target.value })}
            required
          />
        </label>
        <label>
          Temperature
          <input
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={config.temperature}
            onChange={(event) =>
              setConfig({ ...config, temperature: Number(event.target.value) })
            }
            required
          />
        </label>
        <label>
          Max tokens
          <input
            type="number"
            min={1}
            max={4000}
            value={config.max_tokens}
            onChange={(event) =>
              setConfig({ ...config, max_tokens: Number(event.target.value) })
            }
            required
          />
        </label>
        <label>
          Memory type
          <input
            type="text"
            value={config.memory_type}
            onChange={(event) => setConfig({ ...config, memory_type: event.target.value })}
            required
          />
        </label>
        <label>
          Reasoning strategy
          <input
            type="text"
            value={config.reasoning_strategy}
            onChange={(event) =>
              setConfig({ ...config, reasoning_strategy: event.target.value })
            }
            required
          />
        </label>
      </div>

      <label className="agent-form-textarea">
        System prompt
        <textarea
          value={config.system_prompt || ""}
          onChange={(event) => setConfig({ ...config, system_prompt: event.target.value })}
          placeholder="Provide optional system guidance for this agent"
          rows={3}
        />
      </label>

      <div className="agent-form-tools">
        <span>Tools</span>
        <div className="tool-checkbox-grid">
          {availableTools.map((tool) => (
            <label key={tool.id}>
              <input
                type="checkbox"
                checked={tools.includes(tool.name)}
                onChange={() => toggleTool(tool.name)}
              />
              <span>{tool.name}</span>
            </label>
          ))}
        </div>
      </div>

      {error ? <p className="agent-form-error">{error}</p> : null}

      <div className="agent-form-actions">
        <button type="button" onClick={onCancel} className="secondary">
          Cancel
        </button>
        <button type="submit" className="primary" disabled={submitting}>
          {submitting ? "Creating..." : "Create agent"}
        </button>
      </div>
    </form>
  );
}

export default AgentForm;
