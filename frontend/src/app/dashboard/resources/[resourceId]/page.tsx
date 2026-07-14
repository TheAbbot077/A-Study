import { ResourceDetail } from "@/features/dashboard/ResourceDetail";

type ResourceDetailPageProps = {
  params: Promise<{
    resourceId: string;
  }>;
};

export default async function ResourceDetailPage({ params }: ResourceDetailPageProps) {
  const { resourceId } = await params;
  return <ResourceDetail resourceId={resourceId} />;
}
