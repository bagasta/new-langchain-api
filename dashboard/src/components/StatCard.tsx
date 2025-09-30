interface StatCardProps {
  label: string;
  value: string | number;
  helper?: string;
}

function StatCard({ label, value, helper }: StatCardProps) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {helper ? <span className="stat-helper">{helper}</span> : null}
    </div>
  );
}

export default StatCard;
