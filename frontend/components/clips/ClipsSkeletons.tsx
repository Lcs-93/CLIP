import { Skeleton } from "@/components/ui/skeleton";

export function ClipGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={`clip-skeleton-${index}`}
          className="overflow-hidden rounded-[1.35rem] border border-border/65 bg-card/75 p-3 shadow-[0_20px_56px_-42px_rgba(15,23,42,0.45)] backdrop-blur-xl"
        >
          <Skeleton className="aspect-video w-full rounded-xl" />
          <Skeleton className="mt-3 h-4 w-2/3" />
          <Skeleton className="mt-2 h-3 w-1/2" />
          <div className="mt-4 flex items-center justify-between gap-2">
            <Skeleton className="h-8 w-24 rounded-full" />
            <Skeleton className="h-8 w-24 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ClipInspectSkeleton() {
  return (
    <div className="rounded-[1.5rem] border border-border/65 bg-card/78 p-4 shadow-[0_22px_62px_-40px_rgba(15,23,42,0.52)] backdrop-blur-xl">
      <Skeleton className="aspect-video w-full rounded-xl" />
      <Skeleton className="mt-4 h-5 w-3/4" />
      <Skeleton className="mt-3 h-4 w-1/2" />
      <div className="mt-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
      </div>
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-10 flex-1 rounded-xl" />
        <Skeleton className="h-10 w-28 rounded-xl" />
      </div>
    </div>
  );
}
