import { redirect } from "next/navigation";

export default function VideoRootPage({ params }: { params: { videoId: string } }) {
  redirect(`/clips?videoId=${params.videoId}`);
}
