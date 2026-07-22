import { SelfStudyPlanExperience } from "@/features/self-study/SelfStudyPlanExperience";

export default async function SelfStudyWorkspacePlanPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <SelfStudyPlanExperience workspaceId={workspaceId} />;
}
