import { apiRequest } from "@/services/api";

export type Subject = {
  id: string;
  institution?: string | null;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LearningResource = {
  id: string;
  institution?: string | null;
  subject: string;
  curriculum?: string | null;
  curriculum_unit?: string | null;
  stored_file?: string | null;
  title: string;
  description: string;
  resource_type: string;
  status: string;
  source_label: string;
  resource_ready_for_learning?: boolean;
  created_at: string;
  updated_at: string;
};

export type ContentSection = {
  id: string;
  learning_resource: string;
  title: string;
  description: string;
  sequence_number: number;
  review_status: string;
  quality_status: string;
  review_notes?: string | null;
  approved_at?: string | null;
  approved_by?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ContentConcept = {
  id: string;
  content_section: string;
  title: string;
  description: string;
  learning_objective: string;
  sequence_number: number;
  review_status: string;
  quality_status: string;
  review_notes?: string | null;
  approved_at?: string | null;
  approved_by?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export async function listSubjects(): Promise<Subject[]> {
  return (await apiRequest<Subject[]>("academic/subjects/")) ?? [];
}

export async function createSubject(payload: {
  name: string;
  code: string;
  description?: string;
}): Promise<Subject> {
  return (await apiRequest<Subject>("academic/subjects/", {
    method: "POST",
    body: JSON.stringify(payload),
  })) as Subject;
}

export async function getSubject(subjectId: string): Promise<Subject> {
  return (await apiRequest<Subject>(`academic/subjects/${subjectId}/`)) as Subject;
}

export async function listResourcesForSubject(subjectId: string): Promise<LearningResource[]> {
  return (await apiRequest<LearningResource[]>(`academic/learning-resources/?subject=${encodeURIComponent(subjectId)}`)) ?? [];
}

export async function getLearningResource(resourceId: string): Promise<LearningResource> {
  return (await apiRequest<LearningResource>(`academic/learning-resources/${resourceId}/`)) as LearningResource;
}

export async function listSectionsForResource(resourceId: string): Promise<ContentSection[]> {
  return (
    (await apiRequest<ContentSection[]>(`academic/content-sections/?learning_resource=${encodeURIComponent(resourceId)}`)) ?? []
  );
}

export async function getContentSection(sectionId: string): Promise<ContentSection> {
  return (await apiRequest<ContentSection>(`academic/content-sections/${sectionId}/`)) as ContentSection;
}

export async function listConceptsForResource(resourceId: string): Promise<ContentConcept[]> {
  return (
    (await apiRequest<ContentConcept[]>(`academic/content-concepts/?learning_resource=${encodeURIComponent(resourceId)}`)) ?? []
  );
}

export async function getContentConcept(conceptId: string): Promise<ContentConcept> {
  return (await apiRequest<ContentConcept>(`academic/content-concepts/${conceptId}/`)) as ContentConcept;
}

export async function createLearningResource(payload: {
  subject: string;
  stored_file: string;
  title: string;
  description?: string;
  resource_type?: string;
  source_label?: string;
}): Promise<LearningResource> {
  return (await apiRequest<LearningResource>("academic/learning-resources/", {
    method: "POST",
    body: JSON.stringify(payload),
  })) as LearningResource;
}
