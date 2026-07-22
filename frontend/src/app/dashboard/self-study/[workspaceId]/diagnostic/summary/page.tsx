import { SelfStudyDiagnosticExperience } from "@/features/self-study/SelfStudyDiagnosticExperience";

export default async function SelfStudyWorkspaceDiagnosticSummaryPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyDiagnosticExperience mode="summary" workspaceId={workspaceId} />;
}
