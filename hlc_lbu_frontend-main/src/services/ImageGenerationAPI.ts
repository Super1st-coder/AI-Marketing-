export { type ImagePrompt } from "@/utils/type-declarations";
import { ImagePrompt2 } from "@/utils/type-declarations";
import { ImageGeneration } from "@/components/images/image-generation/ImageGenerator.vue";

export type ImageAttributes = Record<string, string>;

export default {
  // servicio 14/18 de la fase 2 :  Choose one buyer that fits your hypothesis (Generate image prompts) 14
  async generate(prompt: string, signal?: AbortSignal): Promise<Blob> {
    try {
      const response = await $api("/v2/application/hiluca/image/generate", {
        method: "POST",
        responseType: "blob",
        body: {
          prompt,
        },
        signal,
      });

      return response;
    } catch (error: any) {
      throw error;
    }
  },

  mapDataToSchema(
    prompts: ImagePrompt[] | ImagePrompt2[] | null | undefined,
    selectedPrompt?: ImagePrompt | ImagePrompt2 | null,
    image?: Blob | string | null,
  ): ImageGeneration {
    if (!prompts) {
      return undefined;
    }

    // If the selected prompt is not preferred, it is not selected
    if (
      !image ||
      prompts.find((prompt) => prompt.id === selectedPrompt?.id)?.preferred !==
        1
    ) {
      selectedPrompt = undefined;
      image = undefined;
    }

    return {
      prompts: prompts.map((prompt: ImagePrompt | ImagePrompt2) =>
        "description" in prompt ? prompt.description : prompt.prompt,
      ),
      selectedPromptIndex: selectedPrompt?.id ?? undefined,
      selectedPrompt: selectedPrompt
        ? "description" in selectedPrompt
          ? selectedPrompt.description
          : selectedPrompt.prompt
        : undefined,
      generatedImage: selectedPrompt ? image : undefined,
    };
  },
};
