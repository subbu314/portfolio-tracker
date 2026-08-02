import { Skeleton } from "@/components/ui/skeleton";

type Variant =
  | "overview"
  | "holdings"
  | "holding-detail"
  | "settings-auth"
  | "settings-benchmarks";

export function PageSkeleton({ variant }: { variant: Variant }) {
  if (variant === "overview") {
    return (
      <div className="stack" data-testid="page-skeleton">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-5 md:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }
  if (variant === "holdings") {
    return (
      <div className="stack" data-testid="page-skeleton">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-28" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }
  if (variant === "holding-detail") {
    return (
      <div className="stack" data-testid="page-skeleton">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-20 w-full" />
        <div className="grid gap-5 md:grid-cols-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }
  if (variant === "settings-auth") {
    return (
      <div className="stack" data-testid="settings-auth-skeleton">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }
  return (
    <Skeleton
      className="h-64 w-full"
      data-testid="settings-benchmarks-skeleton"
    />
  );
}
