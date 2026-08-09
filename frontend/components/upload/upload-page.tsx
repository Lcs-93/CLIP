"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

import { useUploadAndProcess } from "@/hooks/use-upload-and-process";
import {
  ProcessingShowcase,
  RainbowRotatingTitle,
  SuccessState,
  UploadDropzone,
  UploadErrorCard,
} from "@/components/upload";

type ViewState = "idle" | "processing" | "done" | "error";
type ProcessingPhase = "idle" | "uploading" | "uploaded" | "analyzing" | "analyzed" | "generating" | "ready" | "error";

const ROTATING_STATUS_BY_PHASE: Record<ProcessingPhase, string[]> = {
  idle: ["Waiting for upload..."],
  uploading: ["Uploading video..."],
  uploaded: ["Extracting audio...", "Preparing analysis..."],
  analyzing: ["Analyzing content...", "Detecting highlights..."],
  analyzed: ["Detecting highlights...", "Preparing clip generation..."],
  generating: ["Generating clips...", "Polishing cut points..."],
  ready: ["Finalizing..."],
  error: ["Processing interrupted."],
};

function toEpoch(value?: string | null) {
  if (!value) return null;
  const epoch = Date.parse(value);
  return Number.isFinite(epoch) ? epoch : null;
}

function resolveProcessingPhase(input: {
  uploadStatus: string;
  processingStep: string;
  videoStatus?: string;
  hasError: boolean;
}): ProcessingPhase {
  const { uploadStatus, processingStep, videoStatus, hasError } = input;
  if (hasError) return "error";
  if (uploadStatus === "uploading") return "uploading";
  if (videoStatus === "ready" || processingStep === "ready") return "ready";
  if (videoStatus === "generating" || processingStep === "generating") return "generating";
  if (videoStatus === "analyzed") return "analyzed";
  if (videoStatus === "analyzing" || processingStep === "analyzing") return "analyzing";
  if (videoStatus === "uploaded" || processingStep === "uploaded") return "uploaded";
  return "idle";
}

function resolveActiveStepIndex(phase: ProcessingPhase) {
  switch (phase) {
    case "uploading":
      return 0;
    case "uploaded":
      return 1;
    case "analyzing":
      return 2;
    case "analyzed":
      return 3;
    case "generating":
      return 4;
    case "ready":
      return 5;
    default:
      return 0;
  }
}

export function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const lastUploadedFileRef = useRef<File | null>(null);
  const processStartRef = useRef<number | null>(null);

  const [isDragActive, setIsDragActive] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [statusTextIndex, setStatusTextIndex] = useState(0);
  const [redirectSeconds, setRedirectSeconds] = useState(2);
  const [elapsedSeconds, setElapsedSeconds] = useState<number | null>(null);

  const {
    activeVideoId,
    activeVideo,
    resumableVideo,
    hasUserStartedUpload,
    uploadState,
    processingState,
    isPolling,
    handleUpload,
    resumeLastProcessing,
    refresh,
  } = useUploadAndProcess();
  // Critical guard: processing UI is visible only after explicit user action in this session.
  const hasProcessingIntent = hasUserStartedUpload;

  const hasError = uploadState.status === "error" || processingState.hasError || activeVideo?.status === "error";
  const phase = resolveProcessingPhase({
    uploadStatus: uploadState.status,
    processingStep: processingState.step,
    videoStatus: activeVideo?.status,
    hasError,
  });

  const isProcessing =
    isPolling ||
    phase === "uploading" ||
    phase === "uploaded" ||
    phase === "analyzing" ||
    phase === "analyzed" ||
    phase === "generating";

  const shouldShowDone = hasProcessingIntent && phase === "ready";

  const viewState: ViewState =
    hasError && hasProcessingIntent
      ? "error"
      : shouldShowDone
        ? "done"
        : isProcessing && hasProcessingIntent
          ? "processing"
          : "idle";
  const clipsHref = activeVideoId ? `/clips?videoId=${activeVideoId}` : "/clips";
  const canResumeLastProcessing = !hasProcessingIntent && Boolean(resumableVideo);

  const statusLines = useMemo(() => ROTATING_STATUS_BY_PHASE[phase], [phase]);
  const statusLabel = statusLines[Math.min(statusTextIndex, statusLines.length - 1)] ?? "Processing...";
  const statusDetail =
    processingState.message && processingState.message !== statusLabel
      ? processingState.message
      : "Usually takes a few minutes.";

  useEffect(() => {
    setStatusTextIndex(0);
  }, [phase]);

  useEffect(() => {
    if (viewState !== "processing" || statusLines.length <= 1) return;
    const interval = window.setInterval(() => {
      setStatusTextIndex((value) => (value + 1) % statusLines.length);
    }, 2400);
    return () => window.clearInterval(interval);
  }, [statusLines, viewState]);

  useEffect(() => {
    if (!activeVideoId) {
      processStartRef.current = null;
      setElapsedSeconds(null);
      return;
    }
    processStartRef.current = null;
  }, [activeVideoId]);

  useEffect(() => {
    if (viewState !== "processing") return;
    if (!processStartRef.current) {
      processStartRef.current = toEpoch(activeVideo?.created_at) ?? Date.now();
    }
    const tick = () => {
      if (!processStartRef.current) return;
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - processStartRef.current) / 1000)));
    };
    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [activeVideo?.created_at, viewState]);

  useEffect(() => {
    if (viewState !== "done") return;
    setRedirectSeconds(2);
    const delayMs = 1800;
    const startedAt = Date.now();

    const countdown = window.setInterval(() => {
      const remainingMs = Math.max(0, delayMs - (Date.now() - startedAt));
      setRedirectSeconds(Math.max(1, Math.ceil(remainingMs / 1000)));
    }, 220);

    const timeout = window.setTimeout(() => {
      router.push(clipsHref);
    }, delayMs);

    return () => {
      window.clearInterval(countdown);
      window.clearTimeout(timeout);
    };
  }, [clipsHref, router, viewState]);

  const beginUpload = useCallback(
    async (file: File) => {
      if (!file) return;
      lastUploadedFileRef.current = file;
      processStartRef.current = Date.now();
      setElapsedSeconds(0);
      try {
        await handleUpload(file);
      } catch {
        // Error state is handled by store/hook.
      }
    },
    [handleUpload]
  );

  const onOpenPicker = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const onInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      void beginUpload(file);
      event.target.value = "";
    },
    [beginUpload]
  );

  const onRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refresh();
    } finally {
      setIsRefreshing(false);
    }
  }, [refresh]);

  const onResumeLastProcessing = useCallback(async () => {
    setIsResuming(true);
    try {
      const video = await resumeLastProcessing();
      const startEpoch = toEpoch(video?.created_at ?? resumableVideo?.created_at) ?? Date.now();
      processStartRef.current = startEpoch;
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startEpoch) / 1000)));
    } finally {
      setIsResuming(false);
    }
  }, [resumeLastProcessing, resumableVideo?.created_at]);

  const onRetry = useCallback(() => {
    const file = lastUploadedFileRef.current;
    if (file) {
      void beginUpload(file);
      return;
    }
    inputRef.current?.click();
  }, [beginUpload]);

  const onReset = useCallback(() => {
    window.location.assign("/");
  }, []);

  const activeStepIndex = resolveActiveStepIndex(phase);

  return (
    <main className="app-page overflow-hidden">
      <section className="app-page-inner z-10 justify-center pb-16 pt-10 sm:pt-12">
        <div className="mx-auto grid w-full max-w-5xl gap-10">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto w-full max-w-4xl"
          >
            <RainbowRotatingTitle />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto w-full max-w-3xl"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={viewState}
                layout
                initial={{ opacity: 0, y: 12, scale: 0.985 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -12, scale: 0.985 }}
                transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
              >
                {viewState === "idle" ? (
                  <UploadDropzone
                    isDragActive={isDragActive}
                    isResuming={isResuming}
                    disabled={uploadState.status === "uploading"}
                    clipsHref={clipsHref}
                    resumeAvailable={canResumeLastProcessing}
                    onResume={onResumeLastProcessing}
                    onOpenPicker={onOpenPicker}
                    onDragEnter={(event) => {
                      event.preventDefault();
                      setIsDragActive(true);
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setIsDragActive(true);
                    }}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      if (event.currentTarget.contains(event.relatedTarget as Node)) return;
                      setIsDragActive(false);
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      setIsDragActive(false);
                      const file = event.dataTransfer.files?.[0];
                      if (!file) return;
                      void beginUpload(file);
                    }}
                  />
                ) : null}

                {viewState === "processing" ? (
                  <ProcessingShowcase
                    statusLabel={statusLabel}
                    statusDetail={statusDetail}
                    activeStepIndex={activeStepIndex}
                    isRefreshing={isRefreshing}
                    elapsedSeconds={elapsedSeconds}
                    clipsHref={clipsHref}
                    canOpenClips={phase === "ready"}
                    onRefresh={onRefresh}
                  />
                ) : null}

                {viewState === "done" ? <SuccessState clipsHref={clipsHref} redirectSeconds={redirectSeconds} /> : null}

                {viewState === "error" ? (
                  <UploadErrorCard
                    message={uploadState.error ?? processingState.message ?? "Upload failed."}
                    canRetry={Boolean(lastUploadedFileRef.current)}
                    onRetry={onRetry}
                    onReset={onReset}
                  />
                ) : null}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>
      </section>
      <input ref={inputRef} type="file" accept="video/*" className="hidden" onChange={onInputChange} />
    </main>
  );
}
