// client/src/components/ProtectedRoute.tsx
import { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/apiClient";
import { Redirect } from "wouter";

interface Props {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const { isLoading, error } = useQuery({
    queryKey: ["auth-check"], // DIFFERENT from Navbar
    queryFn: () => apiFetch("/api/auth/me"), // fresh check
    retry: false,
  });

  // Still checking login session
  if (isLoading) return <div className="text-white p-8">Loading...</div>;

  // User not logged in
  if (error) return <Redirect to="/login" />;

  // User logged in
  return <>{children}</>;
}
