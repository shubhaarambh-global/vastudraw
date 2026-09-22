type VastudrawBrandMarkProps = {
  readonly size?: number;
  readonly className?: string;
};

export function VastudrawBrandMark({
  size = 40,
  className,
}: VastudrawBrandMarkProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="1"
        y="1"
        width="38"
        height="38"
        rx="11"
        className="vastudraw-mark-frame"
      />

      <path d="M9.5 10.5 20 29 30.5 10.5" className="vastudraw-mark-v" />

      <path d="M9.5 10.5h6M30.5 10.5h-6" className="vastudraw-mark-guide" />

      <rect
        x="7.5"
        y="8.5"
        width="4"
        height="4"
        rx="1"
        className="vastudraw-mark-node"
      />

      <rect
        x="28.5"
        y="8.5"
        width="4"
        height="4"
        rx="1"
        className="vastudraw-mark-node"
      />
    </svg>
  );
}
