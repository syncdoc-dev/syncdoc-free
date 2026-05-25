import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

interface DemoCredentials {
  username: string;
  password: string;
  reset_at?: number | null;
}

interface DemoBannerProps {
  credentials: DemoCredentials | null;
}

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return "resetting…";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export default function DemoBanner({ credentials }: DemoBannerProps) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!credentials?.reset_at) return;

    const update = () => {
      const now = Math.floor(Date.now() / 1000);
      const left = credentials.reset_at! - now;
      setRemaining(left);
    };

    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [credentials?.reset_at]);

  if (!credentials) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 text-center text-sm text-amber-200">
      <div className="flex items-center justify-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <span className="font-medium">Demo Environment</span>
        <span className="text-amber-300/80">
          — data resets every 10 minutes
        </span>
      </div>
      <div className="mt-1 text-amber-300/70">
        Log in with{" "}
        <code className="bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-200 font-mono text-xs">
          {credentials.username}
        </code>
        /
        <code className="bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-200 font-mono text-xs">
          {credentials.password}
        </code>
      </div>
      {remaining !== null && remaining > 0 && (
        <div className="mt-1 text-xs text-amber-300/60 font-mono">
          Next reset in {formatCountdown(remaining)}
        </div>
      )}
    </div>
  );
}
