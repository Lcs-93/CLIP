import Link from "next/link";
import { Film, Loader2, SearchX, UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  mode: "no-videos" | "no-clips" | "no-results";
  isProcessing?: boolean;
  onResetFilters?: () => void;
}

export function EmptyState({ mode, isProcessing, onResetFilters }: EmptyStateProps) {
  if (mode === "no-videos") {
    return (
      <div className="rounded-[1.6rem] border border-border/70 bg-card/78 px-6 py-12 text-center shadow-[0_28px_80px_-56px_rgba(15,23,42,0.5)] backdrop-blur-xl">
        <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full border border-border/70 bg-background/80 text-muted-foreground">
          <UploadCloud className="h-5 w-5" />
        </div>
        <p className="mt-4 text-base font-semibold text-foreground">No source video found</p>
        <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
          Upload a source video to start generating clips in the workspace.
        </p>
        <div className="mt-5">
          <Button asChild className="rounded-full px-6">
            <Link href="/">Go to upload</Link>
          </Button>
        </div>
      </div>
    );
  }

  if (mode === "no-results") {
    return (
      <div className="rounded-[1.6rem] border border-border/70 bg-card/78 px-6 py-12 text-center shadow-[0_28px_80px_-56px_rgba(15,23,42,0.5)] backdrop-blur-xl">
        <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full border border-border/70 bg-background/80 text-muted-foreground">
          <SearchX className="h-5 w-5" />
        </div>
        <p className="mt-4 text-base font-semibold text-foreground">No clips match these filters</p>
        <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
          Adjust the score, search, or duration filters to reveal more clips.
        </p>
        {onResetFilters ? (
          <div className="mt-5">
            <Button variant="outline" className="rounded-full px-6" onClick={onResetFilters}>
              Reset filters
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="rounded-[1.6rem] border border-border/70 bg-card/78 px-6 py-12 text-center shadow-[0_28px_80px_-56px_rgba(15,23,42,0.5)] backdrop-blur-xl">
      <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full border border-border/70 bg-background/80 text-muted-foreground">
        {isProcessing ? <Loader2 className="h-5 w-5 animate-spin" /> : <Film className="h-5 w-5" />}
      </div>
      <p className="mt-4 text-base font-semibold text-foreground">No clips available</p>
      <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
        {isProcessing
          ? "The video is still processing. New clips will appear here automatically."
          : "Clip generation returned no result for this source video."}
      </p>
    </div>
  );
}
