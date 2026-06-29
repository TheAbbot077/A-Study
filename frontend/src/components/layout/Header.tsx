export function Header() {
  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-background)]/95">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-[var(--color-foreground)]">
            Abbot Study
          </h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            AI-native learning OS
          </p>
        </div>
      </div>
    </header>
  );
}
