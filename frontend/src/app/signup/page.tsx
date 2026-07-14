import { Suspense } from "react";
import { LoadingState } from "@/components/feedback";
import { AuthForm } from "@/features/auth";

export default function SignupPage() {
  return (
    <Suspense fallback={<LoadingState message="Opening sign up..." />}>
      <AuthForm mode="signup" />
    </Suspense>
  );
}
