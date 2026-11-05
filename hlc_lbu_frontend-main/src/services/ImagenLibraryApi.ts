import { handleCommonErrors } from "./common-errors";
import type { UnsplashSearchResponse } from "@/types/unsplash";

export type GoogleDriveImage = {
  id: string;
  base64: string;
  data_uri: string;
  mimeType: string;
  name: string;
  publicUrl: string;
  webContentLink: string;
  webViewLink: string;
  createdTime?: string;
  folderId?: string;
};

export type ImagesFromLibraryResponse = {
  total: number;
  data: {
    id: string;
    url: string;
    category: string;
    description: string;
  }[];
};

export default {
  async getImagesFromLibrary(
    brandId: number,
    limit: number,
    start: number,
    category?: string | undefined,
    description?: string | undefined,
  ): Promise<ImagesFromLibraryResponse> {
    try {
      return await $api<any>("/v2/application/hiluca/image_library", {
        method: "GET",
        cache: "no-cache",
        params: {
          limit,
          start,
          filter: {
            category,
            description,
          },
          brand: brandId,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getUnsplashImages(
    per_page: number,
    page: number,
    query: string,
    options?: { orientation?: string; color?: string; content_filter?: string },
  ): Promise<UnsplashSearchResponse> {
    try {
      const params = new URLSearchParams();
      params.set("per_page", String(per_page));
      params.set("page", String(page));
      params.set("q", query);
      if (options?.orientation) params.set("orientation", options.orientation);
      if (options?.color) params.set("color", options.color);
      if (options?.content_filter)
        params.set("content_filter", options.content_filter);

      return await $api<UnsplashSearchResponse>(
        `/v2/external/unsplash/images/search?${params.toString()}`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async fetchGoogleDriveImages(userEmail: string): Promise<any> {
    try {
      return await $api<any>(`/v2/external/google-drive/list/${userEmail}`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async fetchGoogleDriveImageBinary(
    userEmail: string,
    folderId: string,
    imageName: string,
  ): Promise<any> {
    try {
      return await $api<any>(
        `/v2/external/google-drive/image/download/${userEmail}/${folderId}/${imageName}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async uploadImagesToGoogleDrive(
    userEmail: string,
    image: File,
  ): Promise<any> {
    try {
      const formData = new FormData();
      formData.append("file", image);
      return await $api<any>(`/v2/external/google-drive/upload/${userEmail}`, {
        method: "POST",
        body: formData,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async validateGoogleDriveAuth(userEmail: string): Promise<any> {
    try {
      return await $api<any>(`/v2/external/google-drive/status/${userEmail}`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
