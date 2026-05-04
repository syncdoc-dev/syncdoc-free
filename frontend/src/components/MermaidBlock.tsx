import { useEffect, useId, useState } from "react";
import mermaid from "mermaid";

function normalizeIndentation(chart: string) {
  return chart
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.replace(/^\s{4}/, "").replace(/\s+$/, ""))
    .join("\n")
    .trim();
}

function sanitizeMermaid(chart: string) {
  const normalized = normalizeIndentation(chart);
  const lines = normalized.split("\n");
  if (lines.length === 0) {
    return normalized;
  }

  const [firstLine, ...rest] = lines;
  const fixedFirstLine = firstLine.replace(/^graph\s+/i, "flowchart ").replace(/;$/, "");
  const cleanedRest = rest
    .map((line) => {
      const withQuotedNodes = line.replace(/\[([^\]"]+)\]/g, (_, label: string) => {
        const escaped = label.replace(/"/g, "&quot;");
        return `["${escaped}"]`;
      });
      return withQuotedNodes.replace(/\|([^|]+)\|/g, (_, label: string) => {
        const compact = label.replace(/\s+/g, " ").trim();
        const escaped = compact.replace(/"/g, "&quot;");
        return `|"${escaped}"|`;
      });
    })
    .filter((line, index, arr) => {
      if (line.trim()) return true;
      const prev = arr[index - 1]?.trim();
      const next = arr[index + 1]?.trim();
      return prev === "end" || next === "end";
    });

  return [fixedFirstLine, ...cleanedRest].join("\n");
}

function toErrorMessage(err: unknown) {
  if (err instanceof Error && err.message) {
    return err.message;
  }

  if (typeof err === "string") {
    return err;
  }

  try {
    return JSON.stringify(err);
  } catch {
    return "Failed to render Mermaid diagram";
  }
}

function getThemeValue(name: string, fallback: string) {
  if (typeof window === "undefined") {
    return fallback;
  }

  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function getMermaidConfig() {
  return {
    startOnLoad: false,
    theme: "base" as const,
    securityLevel: "strict" as const,
    fontFamily:
      "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    flowchart: {
      useMaxWidth: false,
      htmlLabels: false,
      nodeSpacing: 48,
      rankSpacing: 72,
      padding: 24,
    },
    themeVariables: {
      background: getThemeValue("--bg-input", "#141c18"),
      primaryColor: getThemeValue("--bg-secondary", "#0e1411"),
      primaryTextColor: getThemeValue("--text-white", "#e7fff7"),
      primaryBorderColor: getThemeValue("--border-light", "#26352e"),
      lineColor: getThemeValue("--text-muted", "#89a79d"),
      tertiaryColor: getThemeValue("--accent-bg", "rgba(32, 201, 151, 0.16)"),
      tertiaryTextColor: getThemeValue("--text-white", "#e7fff7"),
      tertiaryBorderColor: getThemeValue("--accent-strong", "#20c997"),
      clusterBkg: getThemeValue("--bg-card", "rgba(14, 20, 17, 0.65)"),
      clusterBorder: getThemeValue("--accent-strong", "#20c997"),
      edgeLabelBackground: getThemeValue("--bg-input", "#141c18"),
      nodeBorder: getThemeValue("--border-light", "#26352e"),
      mainBkg: getThemeValue("--bg-secondary", "#0e1411"),
      secondBkg: getThemeValue("--bg-card", "rgba(14, 20, 17, 0.65)"),
      textColor: getThemeValue("--text-primary", "#d9f7ef"),
      fontSize: "13px",
    },
  };
}

async function renderChart(id: string, chart: string) {
  mermaid.initialize(getMermaidConfig());

  return mermaid.render(id, chart);
}

export default function MermaidBlock({ chart }: { chart: string }) {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [attemptedChart, setAttemptedChart] = useState<string>("");
  const id = useId();

  useEffect(() => {
    let cancelled = false;
    const rawChart = normalizeIndentation(chart);
    const fallbackChart = sanitizeMermaid(chart);

    async function render() {
      try {
        const result = await renderChart(`mermaid-${id.replace(/[:]/g, "-")}`, rawChart);
        if (!cancelled) {
          setSvg(result.svg);
          setError("");
          setAttemptedChart(rawChart);
        }
      } catch (firstError) {
        try {
          const result = await renderChart(
            `mermaid-${id.replace(/[:]/g, "-")}-sanitized`,
            fallbackChart,
          );
          if (!cancelled) {
            setSvg(result.svg);
            setError("");
            setAttemptedChart(fallbackChart);
          }
        } catch (secondError) {
          if (!cancelled) {
            setError(
              `${toErrorMessage(firstError)}${fallbackChart !== rawChart ? `\n\nRetry: ${toErrorMessage(secondError)}` : ""}`,
            );
            setSvg("");
            setAttemptedChart(fallbackChart);
          }
        }
      }
    }

    void render();

    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return (
      <div className="my-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
        <div className="mb-2 text-sm font-medium text-amber-300">Mermaid render error</div>
        <pre className="mb-3 overflow-auto whitespace-pre-wrap text-xs text-amber-200">{error}</pre>
        <pre className="overflow-auto whitespace-pre-wrap rounded-lg bg-[var(--bg-input)] p-4 text-xs text-amber-100">
          {attemptedChart || chart}
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-4 rounded-xl border border-[var(--border)] bg-[var(--bg-input)] p-4 text-sm text-[var(--text-secondary)]">
        Rendering diagram...
      </div>
    );
  }

  return (
    <details className="my-4 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-input)]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-[var(--text-primary)] marker:hidden">
        <span>Architecture Diagram</span>
        <span className="text-xs font-normal text-[var(--text-muted)]">
          Expand Mermaid view
        </span>
      </summary>
      <div className="border-t border-[var(--border)] overflow-x-auto overflow-y-hidden p-6">
        <div
          className="flex justify-center [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-none [&_svg]:overflow-visible"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>
    </details>
  );
}
