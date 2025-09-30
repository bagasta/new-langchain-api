import { ToolResponse } from "../api/tools";

interface ToolGridProps {
  tools: ToolResponse[];
  loading: boolean;
}

function ToolGrid({ tools, loading }: ToolGridProps) {
  if (loading) {
    return <p className="muted">Loading tools...</p>;
  }

  if (!tools.length) {
    return <p className="muted">No tools available.</p>;
  }

  return (
    <div className="tool-grid">
      {tools.map((tool) => (
        <div key={tool.id} className="tool-card">
          <h4>{tool.name}</h4>
          <span className="tool-type">{tool.type}</span>
          {tool.description ? <p>{tool.description}</p> : null}
        </div>
      ))}
    </div>
  );
}

export default ToolGrid;
