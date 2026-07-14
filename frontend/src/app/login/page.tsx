import { Suspense } from "react";
import { LoadingState } from "@/components/feedback";
import { AuthForm } from "@/features/auth";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingState message="Opening login..." />}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
