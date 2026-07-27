import { apiRequest } from "@/services/api";

export type LearningIdentityProfileListItem = {
  profile_id: string;
  tenant_id: string;
  learner_id: string;
  status: string;
  profile_version: number;
  updated_at: string;
};

export type LearningMemoryItem = {
  id: string;
  kind: "attribute" | "observation" | "preference";
  label: string;
  value: string;
  classification: string;
  source_summary: string;
  last_updated_at: string;
  status: string;
  currently_used: boolean;
  allowed_actions: string[];
};

export type LearningIdentitySummary = {
  profile_id: string;
  tenant_id: string;
  learner_id: string;
  status: string;
  profile_version: number;
  current_version_number: number | null;
  what_abbot_remembers: LearningMemoryItem[];
  recent_learning_activity: LearningMemoryItem[];
  study_preferences: LearningMemoryItem[];
  allowed_actions: string[];
};

export type LearningTimelineEntry = {
  timeline_id: string;
  occurred_at: string;
  recorded_at: string;
  event_type: string;
  title: string;
  description: string;
  classification: string;
  disposition: string;
  source_summary: string;
  related_profile_version: number | null;
};

export type LearningTimeline = {
  profile_id: string;
  entries: LearningTimelineEntry[];
};

export type PreferencePayload = {
  expected_profile_version: number;
  preference_key: string;
  value: unknown;
  idempotency_key?: string;
};

export async function listLearningIdentityProfiles(signal?: AbortSignal): Promise<LearningIdentityProfileListItem[]> {
  return (await apiRequest<LearningIdentityProfileListItem[]>("learning-identity/profiles/", { signal })) ?? [];
}

export async function getLearningIdentitySummary(profileId: string, signal?: AbortSignal): Promise<LearningIdentitySummary> {
  const response = await apiRequest<LearningIdentitySummary>(`learning-identity/profiles/${profileId}/`, { signal });
  if (!response) throw new Error("Learning identity summary was empty.");
  return response;
}

export async function getLearningIdentityTimeline(profileId: string, signal?: AbortSignal): Promise<LearningTimeline> {
  const response = await apiRequest<LearningTimeline>(`learning-identity/profiles/${profileId}/timeline/`, { signal });
  if (!response) throw new Error("Learning identity timeline was empty.");
  return response;
}

export async function setLearningPreference(profileId: string, payload: PreferencePayload): Promise<{ preference_id: string; preference_key: string; status: string; version: number }> {
  const response = await apiRequest<{ preference_id: string; preference_key: string; status: string; version: number }>(`learning-identity/profiles/${profileId}/preferences/`, { method: "POST", body: JSON.stringify(payload) });
  if (!response) throw new Error("Learning preference response was empty.");
  return response;
}
