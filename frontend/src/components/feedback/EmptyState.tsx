type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-background)] p-6">
      <h2 className="text-base font-semibold text-[var(--color-foreground)]">{title}</h2>
      {description ? (
        <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{description}</p>
      ) : null}
    </div>
  );
}
