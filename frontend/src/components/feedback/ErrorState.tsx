type ErrorStateProps = {
  title?: string;
  message?: string;
};

export function ErrorState({
  title = "Something went wrong",
  message = "Please try again.",
}: ErrorStateProps) {
  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-background)] p-6"
      role="alert"
    >
      <h2 className="text-base font-semibold text-[var(--color-foreground)]">{title}</h2>
      <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{message}</p>
    </div>
  );
}
