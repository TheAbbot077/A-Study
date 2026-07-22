export type PopulationStatus = "planned" | "populating" | "populated" | "failed";
export type PopulationMapping = { academic_section_id: string; outcome: "created" | "matched"; sequence_number: number };
export type AcademicPopulationRun = {
  id: string; approved_projection_id: string; approval_decision_id: string; resource_id: string;
  subject_id: string; status: PopulationStatus; projection_fingerprint: string;
  created_section_count: number; matched_section_count: number; created_concept_count: number;
  matched_concept_count: number; failure_code: string; failure_message: string;
  started_at: string | null; completed_at: string | null; failed_at: string | null;
};
