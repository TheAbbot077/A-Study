import { SelfStudyDiagnosticExperience } from "@/features/self-study/SelfStudyDiagnosticExperience";

export default async function SelfStudyWorkspaceDiagnosticPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyDiagnosticExperience workspaceId={workspaceId} />;
}
