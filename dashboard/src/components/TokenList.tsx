import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import { UserToken } from "../api/user";

dayjs.extend(relativeTime);

interface TokenListProps {
  tokens: UserToken[];
  loading: boolean;
}

function TokenList({ tokens, loading }: TokenListProps) {
  if (loading) {
    return <p className="muted">Loading tokens...</p>;
  }

  if (!tokens.length) {
    return <p className="muted">No connected services yet.</p>;
  }

  return (
    <div className="token-table-wrapper">
      <table className="token-table">
        <thead>
          <tr>
            <th>Service</th>
            <th>Scope</th>
            <th>Expires</th>
            <th>Connected</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => (
            <tr key={token.id}>
              <td>{token.service}</td>
              <td>{Array.isArray(token.scope) ? token.scope.join(", ") : token.scope}</td>
              <td>{token.expires_at ? dayjs(token.expires_at).fromNow() : "N/A"}</td>
              <td>{dayjs(token.created_at).format("YYYY-MM-DD HH:mm")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default TokenList;
