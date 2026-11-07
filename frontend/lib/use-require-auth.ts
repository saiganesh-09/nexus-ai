"use client";

import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";
import { getToken } from "./auth";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("nexus-auth-change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("nexus-auth-change", callback);
  };
}

const getSnapshot = () => getToken() !== null;
const getServerSnapshot = () => false;

/** Returns true when a session token exists; redirects to /login otherwise. */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const hasToken = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (!hasToken) router.replace("/login");
  }, [hasToken, router]);

  return hasToken;
}
