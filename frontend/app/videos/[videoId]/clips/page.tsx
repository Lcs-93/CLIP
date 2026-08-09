import { redirect } from "next/navigation";

export default function LegacyVideoClipsPage({ params }: { params: { videoId: string } }) {
  redirect(`/clips?videoId=${params.videoId}`);
}
