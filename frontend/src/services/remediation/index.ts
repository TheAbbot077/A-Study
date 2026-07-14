import { apiRequest } from "@/services/api";

export type RemediationPlan = {
  id: string;
  status: string;
  rationale: string;
};

export async function startRemediationPlan(planId: string): Promise<RemediationPlan> {
  return (await apiRequest<RemediationPlan>(`remediation/plans/${planId}/start/`, {
    method: "POST",
    body: JSON.stringify({}),
  })) as RemediationPlan;
}
