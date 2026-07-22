import { SelfStudyWorkspace } from "@/features/self-study/SelfStudyWorkspace";

export default async function SelfStudyWorkspaceLearnPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyWorkspace section="learn" workspaceId={workspaceId} />;
}
