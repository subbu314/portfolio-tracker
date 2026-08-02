import { HoldingDetailPage } from "@/components/HoldingDetailPage";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const instrumentId = Number(id);
  if (!Number.isFinite(instrumentId)) {
    return <p role="alert">Invalid holding</p>;
  }
  return <HoldingDetailPage instrumentId={instrumentId} />;
}
