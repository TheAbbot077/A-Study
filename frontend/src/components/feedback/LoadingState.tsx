type LoadingStateProps = {
  message?: string;
};

export function LoadingState({ message = "Loading..." }: LoadingStateProps) {
  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 text-center"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm text-[var(--color-muted-foreground)]">{message}</p>
    </div>
  );
}
