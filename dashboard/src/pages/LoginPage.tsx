import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import Loader from "../components/Loader";
import { useAuth } from "../context/AuthContext";
import "../styles/auth.css";

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, token } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || "/";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      console.error(err);
      const detail =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail || "Login failed. Please check your credentials and try again.");
    }
  };

  if (loading && !token) {
    return <Loader message="Signing you in..." />;
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>LangChain Dashboard</h1>
        <p className="auth-subtitle">Manage your agents, tools, and executions.</p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error ? <p className="auth-error">{error}</p> : null}
          <button type="submit" className="auth-primary">Log In</button>
        </form>
        <p className="auth-footer">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
