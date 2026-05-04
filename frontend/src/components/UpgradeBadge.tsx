interface UpgradeBadgeProps {
  label?: string;
}

export default function UpgradeBadge({
  label = "Upgrade License",
}: UpgradeBadgeProps) {
  return (
    <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-amber-300">
      {label}
    </span>
  );
}
