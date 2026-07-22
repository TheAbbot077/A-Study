import type {
  ReviewFinding,
  ReviewItem,
  ReviewSession,
  ReviewSessionStatus,
} from "@/services/academic-review";

export type ReviewLifecycle = {
  label: string;
  editable: boolean;
  explanation: string;
};

export function reviewLifecycle(status: ReviewSessionStatus): ReviewLifecycle {
  const values: Record<ReviewSessionStatus, ReviewLifecycle> = {
    not_started: { label: "Not started", editable: false, explanation: "This review has not started." },
    in_progress: { label: "In progress", editable: true, explanation: "Review decisions may be saved." },
    ready_for_approval: { label: "Review completed", editable: false, explanation: "The completed review is ready for a later approval step." },
    approved: { label: "Approved", editable: false, explanation: "This review is closed." },
    approved_with_edits: { label: "Approved with edits", editable: false, explanation: "This review is closed." },
    rejected: { label: "Rejected", editable: false, explanation: "This review is closed." },
    reprocess_requested: { label: "Reprocessing requested", editable: false, explanation: "A replacement proposal is expected." },
    superseded: { label: "Superseded", editable: false, explanation: "A newer review replaced this workspace." },
    abandoned: { label: "Abandoned", editable: false, explanation: "This review is no longer active." },
  };
  return values[status];
}

export function orderedItems(items: ReviewItem[]) {
  return items.map((item, index) => ({ item, backendOrder: index + 1 }));
}

export function reviewCounts(session: ReviewSession) {
  return {
    sections: {
      total: session.summary.section_accepted + session.summary.section_rejected + session.summary.section_pending,
      included: session.summary.section_accepted,
      excluded: session.summary.section_rejected,
      pending: session.summary.section_pending,
    },
    concepts: {
      total: session.summary.concept_accepted + session.summary.concept_rejected + session.summary.concept_pending,
      included: session.summary.concept_accepted,
      excluded: session.summary.concept_rejected,
      pending: session.summary.concept_pending,
    },
  };
}

export function unresolvedFindings(findings: ReviewFinding[]) {
  return findings.filter((finding) => !finding.passed && !finding.resolved);
}

export function severityLabel(severity: ReviewFinding["severity"]) {
  return severity === "blocking" ? "Blocker" : severity === "warning" ? "Warning" : "Information";
}

export function completionSummary(session: ReviewSession, findings: ReviewFinding[]) {
  const counts = reviewCounts(session);
  return {
    ...counts,
    blockerCount: unresolvedFindings(findings).filter((finding) => finding.severity === "blocking").length,
    warningCount: unresolvedFindings(findings).filter((finding) => finding.severity === "warning").length,
    allowed: session.status === "in_progress" && session.summary.ready,
  };
}
