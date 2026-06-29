export type ApiEnvelope<TData> = {
  data: TData;
  message?: string;
  code?: string;
};

export type ApiListResponse<TItem> = {
  results: TItem[];
  count?: number;
  next?: string | null;
  previous?: string | null;
};
