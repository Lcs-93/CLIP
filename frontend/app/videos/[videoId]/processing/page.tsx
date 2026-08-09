import { redirect } from "next/navigation";

export default function LegacyProcessingPage({ params }: { params: { videoId: string } }) {
  redirect(`/?videoId=${params.videoId}`);
}
