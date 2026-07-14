import { AssessmentExperience } from "@/features/dashboard/AssessmentExperience";

type ConceptAssessmentPageProps = {
  params: Promise<{
    conceptId: string;
  }>;
};

export default async function ConceptAssessmentPage({ params }: ConceptAssessmentPageProps) {
  const { conceptId } = await params;
  return <AssessmentExperience conceptId={conceptId} />;
}
