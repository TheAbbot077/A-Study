import { AcademicReviewWorkspace } from "@/features/academic-review";

export default async function AcademicReviewPage({ params }: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await params;
  return <AcademicReviewWorkspace proposalId={proposalId} />;
}
