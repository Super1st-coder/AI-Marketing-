import UtilsApi from "@/services/UtilsApi";
import { ImageStudioGeneratedImage, ImageStudioVariationImage } from "./types";

type DownloadableStudioImage = Pick<
  ImageStudioGeneratedImage | ImageStudioVariationImage,
  "image_url" | "image_blob"
>;

export async function downloadStudioImage(image: DownloadableStudioImage) {
  try {
    const blob =
      image.image_blob ??
      (await UtilsApi.getBinaryFromPresignedUrl(image.image_url));

    const extension = getFileExtensionFromUrl(image.image_url);
    const filename = extension ? `image-studio.${extension}` : "image-studio";

    downloadBlob(blob, filename);
  } catch (e) {
    console.error(e);
  }
}
