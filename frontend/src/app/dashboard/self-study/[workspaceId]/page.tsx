import { SelfStudyWorkspace } from "@/features/self-study/SelfStudyWorkspace";

export default async function SelfStudyWorkspacePage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyWorkspace workspaceId={workspaceId} />;
}
