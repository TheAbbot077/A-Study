import { SubjectDetail } from "@/features/dashboard/SubjectDetail";

type SubjectDetailPageProps = {
  params: Promise<{
    subjectId: string;
  }>;
};

export default async function SubjectDetailPage({ params }: SubjectDetailPageProps) {
  const { subjectId } = await params;
  return <SubjectDetail subjectId={subjectId} />;
}
