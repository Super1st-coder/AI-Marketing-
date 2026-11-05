import { handleCommonErrors } from "../common-errors";

// ─── Types ────────────────────────────────────────────────────────────────────

export type StorageFile = {
  filename: string;
  blob_name: string;
  size: number;
  content_type: string;
  updated: string;
};

export type ListFilesResponse = {
  ok: boolean;
  total: number;
  data: StorageFile[];
};

export type UploadUrlRequest = {
  filename: string;
  content_type: string;
};

/** Shape returned by POST /upload-url */
export type UploadUrlData = {
  upload_url: string; // GCS Resumable Session URL — PUT the file body here
  blob_name: string; // Full GCS path: "{account_id}/{filename}"
  method: "PUT";
  note: string;
};

export type UploadUrlResponse = {
  ok: boolean;
  data: UploadUrlData;
};

export type DeleteFileResponse = {
  ok: boolean;
  message: {
    text: string;
  };
};

// ─── Service ──────────────────────────────────────────────────────────────────

const BASE = (accountId: string | number) => `/v2/storage/${accountId}`;

export default {
  /**
   * GET /api/v2/storage/{account_id}/files
   * Lists all files for the given tenant.
   */
  async listFiles(accountId: string | number): Promise<ListFilesResponse> {
    try {
      return await $api<ListFilesResponse>(`${BASE(accountId)}/files`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  /**
   * POST /api/v2/storage/{account_id}/upload-url
   * Creates a GCS Resumable Upload Session and returns the session URL.
   * The caller must PUT the file body directly to `upload_url` — no auth needed.
   */
  async getUploadUrl(
    accountId: string | number,
    payload: UploadUrlRequest,
  ): Promise<UploadUrlResponse> {
    try {
      return await $api<UploadUrlResponse>(`${BASE(accountId)}/upload-url`, {
        method: "POST",
        body: payload,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  /**
   * Uploads a file directly to GCS using the Resumable Session URL.
   * Raw binary PUT — no Authorization header, no FormData wrapper.
   *
   * @param uploadUrl  The upload_url returned by getUploadUrl()
   * @param file       The File to upload
   * @param onProgress Optional progress callback (0-100)
   */
  async uploadToGcs(
    uploadUrl: string,
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", uploadUrl, true);
      xhr.setRequestHeader(
        "Content-Type",
        file.type || "application/octet-stream",
      );

      if (onProgress) {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        });
      }

      xhr.onload = () => {
        // GCS returns 200 for single-chunk resumable uploads, 201 for multi-chunk completion
        if (xhr.status === 200 || xhr.status === 201 || xhr.status === 204) {
          resolve();
        } else {
          reject(new Error(`GCS upload failed — HTTP ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error("Network error during GCS upload"));
      xhr.send(file); // Send raw file bytes — NOT FormData
    });
  },

  /**
   * POST /api/v2/storage/{account_id}/upload-confirm
   * Cancels the upload session after successful upload to prevent reuse.
   * Call this after uploadToGcs() completes successfully.
   */
  async confirmUpload(
    accountId: string | number,
    uploadUrl: string,
  ): Promise<void> {
    try {
      await $api(`${BASE(accountId)}/upload-confirm`, {
        method: "POST",
        body: { upload_url: uploadUrl },
      });
    } catch (e: unknown) {
      console.error(e);
      // Non-critical — session will expire naturally after 7 days
      console.warn("[StorageApi] Could not cancel upload session:", uploadUrl);
    }
  },

  /**
   * GET /api/v2/storage/{account_id}/files/{filename}/download
   * Downloads a file as a streaming response from the server.
   * Returns a Blob URL suitable for <a href> or window.open().
   */
  async downloadFile(
    accountId: string | number,
    filename: string,
  ): Promise<string> {
    const path = `${BASE(accountId)}/files/${encodeURIComponent(filename)}/download`;
    const blob = await $api<Blob>(path, {
      method: "GET",
      responseType: "blob" as any,
    });
    return URL.createObjectURL(blob);
  },

  /**
   * DELETE /api/v2/storage/{account_id}/files/{filename}
   * Deletes a file from the tenant's GCS folder.
   */
  async deleteFile(
    accountId: string | number,
    filename: string,
  ): Promise<DeleteFileResponse> {
    try {
      return await $api<DeleteFileResponse>(
        `${BASE(accountId)}/files/${encodeURIComponent(filename)}`,
        { method: "DELETE" },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
