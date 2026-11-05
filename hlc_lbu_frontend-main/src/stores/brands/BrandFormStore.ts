import NewBrandsApi, {
  BrandData,
  BrandDataSource,
} from "@/services/NewBrandsApi";
import UtilsApi from "@/services/UtilsApi";

export const useBrandFormStore = defineStore("BrandFormStore", () => {
  const brandId = ref<number>(-1);
  const brand = ref<BrandData>({} as BrandData);
  const dataSources = ref<BrandDataSource[]>([]);
  const pdfBlobs = ref<Record<string, Blob>>({});

  async function refetch({
    refetchDataSources,
  }: { refetchDataSources?: boolean } = {}) {
    const { data } = await NewBrandsApi.getById(brandId.value);
    brand.value = data;

    if (refetchDataSources) {
      // Refetch data sources
      const {
        data: { data_sources: newDataSources },
      } = await NewBrandsApi.getDataSourceList(brandId.value);
      dataSources.value = newDataSources;

      // Download blobs of the PDFs
      const newBlobs = await Promise.all(
        newDataSources
          .filter(
            (dataSource) =>
              dataSource.type === "DOC" && dataSource.presigned_url !== null,
          )
          .map(async (dataSource) => ({
            name: dataSource.name,
            blob: await UtilsApi.getBinaryFromPresignedUrl(
              dataSource.presigned_url,
            ),
          })),
      );

      // Update ref of blobs
      pdfBlobs.value = {};
      newBlobs.forEach((result) => {
        pdfBlobs.value[result.name] = result.blob;
      });
    }
  }

  async function initialize(_brandId: number) {
    brandId.value = _brandId;
    await refetch({ refetchDataSources: true });
  }

  async function free() {
    pdfBlobs.value = {};
  }

  const isIdentityCompleted = computed(() => brand.value.identity.complete);

  const areLogosCompleted = computed(() =>
    !Array.isArray(brand.value.logos) ? brand.value.logos.complete : false,
  );

  const areColorsCompleted = computed(() =>
    !Array.isArray(brand.value.colors) ? brand.value.colors.complete : false,
  );

  const areTypographiesCompleted = computed(() =>
    !Array.isArray(brand.value.typography)
      ? brand.value.typography.complete
      : false,
  );

  const areDosAndDontsCompleted = computed(() => true);

  const isCompleted = computed(
    () =>
      isIdentityCompleted.value &&
      areLogosCompleted.value &&
      areColorsCompleted.value &&
      areTypographiesCompleted.value &&
      areDosAndDontsCompleted.value,
  );

  const displayGlobalAlert = computed(() => {
    const isIdentityCompleted = !!(
      brand.value.identity.about_us?.value &&
      brand.value.identity.mission?.value &&
      brand.value.identity.vision?.value &&
      brand.value.identity.values &&
      brand.value.identity.values.value.length > 0 &&
      brand.value.identity.tone_voice &&
      brand.value.identity.tone_voice.value.length > 0
    );

    const areLogosCompleted =
      Array.isArray(brand.value.logos) &&
      brand.value.logos.some((logo) => logo.category === "main-logo");

    const areColorsCompleted =
      Array.isArray(brand.value.colors) &&
      brand.value.colors.some((color) => color.category === "primary");

    const areTypographiesCompleted =
      Array.isArray(brand.value.typography) &&
      brand.value.typography.length > 0;

    return brand.value.complete
      ? false
      : !(
          isIdentityCompleted &&
          areLogosCompleted &&
          areColorsCompleted &&
          areTypographiesCompleted
        );
  });

  return {
    initialize,
    refetch,
    free,
    brandId,
    brand,
    dataSources,
    pdfBlobs,
    isIdentityCompleted,
    areLogosCompleted,
    areColorsCompleted,
    areTypographiesCompleted,
    areDosAndDontsCompleted,
    isCompleted,
    displayGlobalAlert,
  };
});
