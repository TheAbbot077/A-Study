"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";

type LogoutButtonProps = {
  className?: string;
};

export function LogoutButton({ className = "" }: LogoutButtonProps) {
  const { logout } = useAuth();
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    setPending(true);

    try {
      await logout();
      window.location.replace("/");
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      className={className}
      disabled={pending}
      onClick={() => void handleLogout()}
      type="button"
    >
      {pending ? "Logging out..." : "Log out"}
    </button>
  );
}
