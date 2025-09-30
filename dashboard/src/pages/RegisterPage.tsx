import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Loader from "../components/Loader";
import { useAuth } from "../context/AuthContext";
import "../styles/auth.css";

function RegisterPage() {
  const navigate = useNavigate();
  const { register, loading, token } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    try {
      await register(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      console.error(err);
      const detail =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail || "Registration failed. Please try again.");
    }
  };

  if (loading && !token) {
    return <Loader message="Creating your account..." />;
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>Create your account</h1>
        <p className="auth-subtitle">Set up your workspace to manage agents and tools.</p>
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
              minLength={8}
            />
          </label>
          <label>
            Confirm password
            <input
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              required
              minLength={8}
            />
          </label>
          {error ? <p className="auth-error">{error}</p> : null}
          <button type="submit" className="auth-primary">Sign Up</button>
        </form>
        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
