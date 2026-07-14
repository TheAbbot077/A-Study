import { apiRequest } from "@/services/api";

export type StoredFile = {
  id: string;
  original_filename: string;
  stored_filename: string;
  content_type?: string | null;
  size_bytes: number;
  checksum?: string | null;
  provider: string;
  created_at: string;
  updated_at: string;
};

export async function uploadStoredFile(file: File): Promise<StoredFile> {
  const formData = new FormData();
  formData.append("file", file);

  return (await apiRequest<StoredFile>("storage/files/", {
    method: "POST",
    body: formData,
  })) as StoredFile;
}
