import { AnimatePresence, motion } from "framer-motion";

import { ClipCard } from "@/components/clips/ClipCard";
import { ClipEntry } from "@/lib/types";

interface ClipGridProps {
  clips: ClipEntry[];
  selectedClipId: string | null;
  selectedClipIds: string[];
  videoId: string | null;
  onSelectClip: (clip: ClipEntry) => void;
  onPlayClip: (clip: ClipEntry) => void;
  onToggleSelectClip: (clip: ClipEntry) => void;
}

function clipEditHref(clipId: string, videoId: string | null) {
  if (!videoId) return `/clips/${clipId}`;
  return `/clips/${clipId}?videoId=${videoId}`;
}

function clipOpenHref(videoId: string | null, clipId: string) {
  const params = new URLSearchParams();
  if (videoId) params.set("videoId", videoId);
  params.set("clipId", clipId);
  const suffix = params.toString();
  return suffix.length > 0 ? `/exports?${suffix}` : "/exports";
}

export function ClipGrid({
  clips,
  selectedClipId,
  selectedClipIds,
  videoId,
  onSelectClip,
  onPlayClip,
  onToggleSelectClip,
}: ClipGridProps) {
  return (
    <motion.div layout className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <AnimatePresence mode="popLayout" initial={false}>
        {clips.map((clip, index) => (
          <motion.div
            key={clip.id}
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            <ClipCard
              clip={clip}
              index={index}
              selected={clip.id === selectedClipId}
              bulkSelected={selectedClipIds.includes(clip.id)}
              editHref={clipEditHref(clip.id, videoId)}
              openHref={clipOpenHref(videoId, clip.id)}
              onSelect={onSelectClip}
              onPlay={onPlayClip}
              onToggleBulkSelect={onToggleSelectClip}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
