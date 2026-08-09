import { Skeleton } from "@/components/ui/skeleton";

export function ExportsListSkeleton({ count = 7 }: { count?: number }) {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={`export-row-skeleton-${index}`}
          className="rounded-2xl border border-border/65 bg-card/76 p-3 shadow-[0_18px_52px_-38px_rgba(15,23,42,0.46)] backdrop-blur-xl"
        >
          <div className="grid gap-3 md:grid-cols-[120px_minmax(0,1fr)_auto] md:items-center">
            <Skeleton className="h-8 w-24 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-8 w-16 rounded-full" />
              <Skeleton className="h-8 w-16 rounded-full" />
              <Skeleton className="h-8 w-8 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ExportInspectSkeleton() {
  return (
    <div className="rounded-[1.45rem] border border-border/65 bg-card/78 p-4 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl">
      <Skeleton className="aspect-video w-full rounded-xl" />
      <Skeleton className="mt-4 h-5 w-3/4" />
      <div className="mt-3 grid gap-2">
        <Skeleton className="h-10 rounded-xl" />
        <Skeleton className="h-10 rounded-xl" />
        <Skeleton className="h-10 rounded-xl" />
      </div>
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-10 flex-1 rounded-xl" />
        <Skeleton className="h-10 w-28 rounded-xl" />
      </div>
    </div>
  );
}
