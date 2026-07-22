import { SelfStudyWorkspace } from "@/features/self-study/SelfStudyWorkspace";

export default async function SelfStudyWorkspaceIntentPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyWorkspace section="intent" workspaceId={workspaceId} />;
}
