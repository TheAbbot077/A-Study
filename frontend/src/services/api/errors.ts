export class ApiError extends Error {
  public readonly status?: number;
  public readonly code?: string;
  public readonly details?: unknown;

  constructor(message: string, status?: number, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export type GovernanceBlocker = {
  code: string;
  message?: string;
  category?: string;
  severity?: string;
  [key: string]: unknown;
};

export type ApiProblem = {
  status: number;
  code: string | null;
  message: string;
  fieldErrors?: Record<string, string[]>;
  blockers?: GovernanceBlocker[];
  correlationId?: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringList(value: unknown): string[] | undefined {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) return undefined;
  return value;
}

export function normalizeApiProblem(error: unknown): ApiProblem {
  if (!(error instanceof ApiError)) {
    return { status: 0, code: "NETWORK_ERROR", message: error instanceof Error ? error.message : "Unable to reach the server." };
  }
  const details = isRecord(error.details) ? error.details : {};
  const detail = typeof details.detail === "string" ? details.detail : null;
  const message = typeof details.message === "string" ? details.message : detail ?? error.message;
  const fieldErrors: Record<string, string[]> = {};
  for (const [field, value] of Object.entries(details)) {
    const messages = stringList(value);
    if (messages) fieldErrors[field] = messages;
  }
  const blockers = Array.isArray(details.blockers)
    ? details.blockers.filter((item): item is GovernanceBlocker => isRecord(item) && typeof item.code === "string")
    : undefined;
  return {
    status: error.status ?? 0,
    code: error.code ?? (typeof details.code === "string" ? details.code : null),
    message,
    ...(Object.keys(fieldErrors).length ? { fieldErrors } : {}),
    ...(blockers?.length ? { blockers } : {}),
    correlationId: typeof details.correlation_id === "string" ? details.correlation_id : null,
  };
}
