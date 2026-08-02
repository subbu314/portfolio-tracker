"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function CallbackContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const exchangedTokenRef = useRef<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (params.get("status") === "error") {
      setError("Zerodha login was cancelled or failed");
      return;
    }
    const token = params.get("request_token");
    if (!token) {
      setError("Missing request_token");
      return;
    }
    if (exchangedTokenRef.current === token) return;
    exchangedTokenRef.current = token;

    void api
      .postCallback(token)
      .then(() => router.replace("/settings"))
      .catch((callbackError: Error) => setError(callbackError.message));
  }, [params, router, attempt]);

  if (error) {
    return (
      <div className="stack" role="alert">
        <p>{error}</p>
        <Link href="/settings">Back to Settings</Link>
        <button
          type="button"
          onClick={() => {
            exchangedTokenRef.current = null;
            setError(null);
            setAttempt((current) => current + 1);
          }}
        >
          Retry
        </button>
      </div>
    );
  }
  return <p>Completing Zerodha login…</p>;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<p>Completing Zerodha login…</p>}>
      <CallbackContent />
    </Suspense>
  );
}
