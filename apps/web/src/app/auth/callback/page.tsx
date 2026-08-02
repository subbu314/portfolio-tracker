"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function CallbackContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("request_token");
    if (!token) {
      setError("Missing request_token");
      return;
    }
    void api
      .postCallback(token)
      .then(() => router.replace("/settings"))
      .catch((callbackError: Error) => setError(callbackError.message));
  }, [params, router]);

  if (error) return <p role="alert">{error}</p>;
  return <p>Completing Zerodha login…</p>;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<p>Completing Zerodha login…</p>}>
      <CallbackContent />
    </Suspense>
  );
}
