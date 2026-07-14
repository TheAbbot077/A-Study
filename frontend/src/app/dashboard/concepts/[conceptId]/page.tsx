import { ConceptDetail } from "@/features/dashboard/ConceptDetail";

type ConceptDetailPageProps = {
  params: Promise<{
    conceptId: string;
  }>;
};

export default async function ConceptDetailPage({ params }: ConceptDetailPageProps) {
  const { conceptId } = await params;
  return <ConceptDetail conceptId={conceptId} />;
}
