import { GovernanceWorkspace } from "@/features/academic-governance";

export default async function GovernancePage({
  params,
  searchParams,
}: {
  params: Promise<{ proposalId: string }>;
  searchParams: Promise<{ session?: string }>;
}) {
  const { proposalId } = await params;
  const { session } = await searchParams;
  return <GovernanceWorkspace proposalId={proposalId} sessionId={session} />;
}
