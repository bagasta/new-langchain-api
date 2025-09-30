import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { login as loginRequest, register as registerRequest } from "../api/auth";
import { fetchProfile, UserProfile } from "../api/user";

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("lc_token"));
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const persistToken = useCallback((nextToken: string | null) => {
    if (nextToken) {
      localStorage.setItem("lc_token", nextToken);
    } else {
      localStorage.removeItem("lc_token");
    }
    setToken(nextToken);
  }, []);

  const loadProfile = useCallback(async () => {
    if (!token) {
      setUser(null);
      return;
    }
    try {
      const profile = await fetchProfile();
      setUser(profile);
    } catch (error) {
      console.error("Failed to load profile", error);
      persistToken(null);
      setUser(null);
    }
  }, [persistToken, token]);

  useEffect(() => {
    const initialise = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      await loadProfile();
      setLoading(false);
    };

    void initialise();
  }, [loadProfile, token]);

  const handleLogin = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      try {
        const auth = await loginRequest({ email: email.trim(), password });
        persistToken(auth.access_token);
        await loadProfile();
      } finally {
        setLoading(false);
      }
    },
    [loadProfile, persistToken],
  );

  const handleRegister = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      try {
        const auth = await registerRequest({ email: email.trim(), password });
        persistToken(auth.access_token);
        await loadProfile();
      } finally {
        setLoading(false);
      }
    },
    [loadProfile, persistToken],
  );

  const handleLogout = useCallback(() => {
    persistToken(null);
    setUser(null);
  }, [persistToken]);

  const refreshProfile = useCallback(async () => {
    await loadProfile();
  }, [loadProfile]);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      login: handleLogin,
      register: handleRegister,
      logout: handleLogout,
      refreshProfile,
    }),
    [handleLogin, handleLogout, handleRegister, loading, refreshProfile, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
