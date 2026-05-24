import { useEffect, useState } from "react";
import { getApiBase } from "../api/client";

interface DemoCredentials {
  username: string;
  password: string;
}

interface Config {
  demo_mode: boolean;
  demo_credentials: DemoCredentials | null;
}

export function useConfig() {
  const [config, setConfig] = useState<Config | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${getApiBase()}/config`)
      .then((res) => {
        if (!res.ok) return null;
        return res.json() as Promise<Config>;
      })
      .then((data) => {
        if (!cancelled) setConfig(data);
      })
      .catch(() => {
        // Config endpoint is optional; fail silently
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { config, isLoading };
}
