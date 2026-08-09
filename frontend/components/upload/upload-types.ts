export type UploadViewState = "idle" | "uploading" | "processing" | "done" | "error";

export interface UploadFileMeta {
  name: string;
  size: number;
}
