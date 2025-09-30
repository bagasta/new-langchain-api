import { useAuth } from "../context/AuthContext";

function TopBar() {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div>
        <h2>Dashboard</h2>
        <p className="muted">Welcome back{user ? `, ${user.email}` : ""}</p>
      </div>
      <button type="button" onClick={logout} className="secondary">
        Log out
      </button>
    </header>
  );
}

export default TopBar;
