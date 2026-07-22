import { SelfStudyWorkspace } from "@/features/self-study/SelfStudyWorkspace";

export default async function SelfStudyWorkspaceMaterialsPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyWorkspace section="materials" workspaceId={workspaceId} />;
}
