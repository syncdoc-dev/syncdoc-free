import { AlertTriangle } from "lucide-react";

interface DemoBannerProps {
  credentials: { username: string; password: string } | null;
}

export default function DemoBanner({ credentials }: DemoBannerProps) {
  if (!credentials) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 text-center text-sm text-amber-200">
      <div className="flex items-center justify-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <span className="font-medium">Demo Environment</span>
        <span className="text-amber-300/80">
          — data resets every 30 minutes
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
    </div>
  );
}
