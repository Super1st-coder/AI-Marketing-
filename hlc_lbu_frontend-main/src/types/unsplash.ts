export interface UnsplashPhotoUrls {
  raw?: string;
  full?: string;
  regular?: string;
  small?: string;
  thumb?: string;
}

export interface UnsplashPhoto {
  id: string;
  alt_description?: string | null;
  description?: string | null;
  urls: UnsplashPhotoUrls;
}

export interface UnsplashSearchResponse {
  total: number;
  total_pages: number;
  results: UnsplashPhoto[];
}
