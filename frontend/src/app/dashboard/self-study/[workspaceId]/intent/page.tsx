import { ConversationalOnboarding } from "@/features/self-study/ConversationalOnboarding";

export default async function SelfStudyWorkspaceIntentPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <ConversationalOnboarding workspaceId={workspaceId} />;
}
