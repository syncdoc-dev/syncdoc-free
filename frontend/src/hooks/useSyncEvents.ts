import { useEffect, useState } from "react";
import { getApiBase } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { SyncEventMessage } from "../types";

function getWebSocketUrl(token: string) {
  const apiBase = getApiBase();
  let wsBase: string;

  if (apiBase.startsWith("https://")) {
    wsBase = apiBase.replace("https://", "wss://");
  } else if (apiBase.startsWith("http://")) {
    wsBase = apiBase.replace("http://", "ws://");
  } else {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const isFrontendDevPort = ["5173", "5174"].includes(window.location.port);
    const host = isFrontendDevPort
      ? `${window.location.hostname}:8000`
      : window.location.host;
    wsBase = `${protocol}${host}/api`;
  }

  return `${wsBase.replace(/\/$/, "")}/ws/sync-events?token=${encodeURIComponent(token)}`;
}

export function useSyncEvents(onEvent: (event: SyncEventMessage) => void) {
  const { token } = useAuth();
  const [status, setStatus] = useState<"offline" | "connecting" | "connected">("offline");

  useEffect(() => {
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("offline");
      return;
    }

    let isActive = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let connectTimeout: number | null = null;
    let attempt = 0;

    const connect = () => {
      setStatus("connecting");
      socket = new WebSocket(getWebSocketUrl(token));
      connectTimeout = window.setTimeout(() => {
        if (socket && socket.readyState === WebSocket.CONNECTING) {
          socket.close();
        }
      }, 5000);

      socket.onopen = () => {
        attempt = 0;
        if (connectTimeout !== null) {
          window.clearTimeout(connectTimeout);
          connectTimeout = null;
        }
        setStatus("connected");
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as SyncEventMessage;
          onEvent(event);
        } catch {
          // Ignore malformed messages.
        }
      };

      socket.onclose = () => {
        if (connectTimeout !== null) {
          window.clearTimeout(connectTimeout);
          connectTimeout = null;
        }
        setStatus("offline");
        if (!isActive) return;
        attempt += 1;
        const delay = Math.min(3000 * attempt, 15000);
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      isActive = false;
      setStatus("offline");
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      if (connectTimeout !== null) {
        window.clearTimeout(connectTimeout);
      }
      socket?.close();
    };
  }, [onEvent, token]);

  return status;
}
