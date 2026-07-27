import { AbbotLearningStudio } from "@/features/self-study/AbbotLearningStudio";

export default async function SelfStudyWorkspaceLearnPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <AbbotLearningStudio workspaceId={workspaceId} />;
}
