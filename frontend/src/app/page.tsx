export default function Home() {
  return (
    <section className="space-y-8">
      <div className="space-y-4">
        <h2 className="text-3xl font-semibold tracking-tight text-[var(--color-foreground)] sm:text-4xl">
          Abbot Study
        </h2>
        <p className="max-w-2xl text-lg text-[var(--color-muted-foreground)]">
          An AI-native education operating system built on ordered, mastery-based learning.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]">
          <h3 className="font-semibold text-[var(--color-foreground)]">Ordered Learning</h3>
          <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
            Deterministic chapter and concept progression.
          </p>
        </article>
        <article className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]">
          <h3 className="font-semibold text-[var(--color-foreground)]">The Abbot</h3>
          <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
            Guidance and coordination for learning journeys.
          </p>
        </article>
        <article className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]">
          <h3 className="font-semibold text-[var(--color-foreground)]">Ariel</h3>
          <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
            AI orchestration for adaptive learning support.
          </p>
        </article>
      </div>
    </section>
  );
}
