"use client";

import AuthWatcher from "@/components/auth/AuthWatcher";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <AuthWatcher>{children}</AuthWatcher>;
}
