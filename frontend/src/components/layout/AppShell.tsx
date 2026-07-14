import type { ReactNode } from "react";
import { AuthProvider } from "@/features/auth";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { Container } from "../ui";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <AuthProvider>
      <div className="flex min-h-screen flex-col bg-[var(--color-background)] text-[var(--color-foreground)]">
        <Header />
        <main className="flex-1 py-8 sm:py-10 lg:py-12">
          <Container>{children}</Container>
        </main>
        <Footer />
      </div>
    </AuthProvider>
  );
}
