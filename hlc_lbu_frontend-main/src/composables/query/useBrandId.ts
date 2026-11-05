export default function useBrandId() {
  const route = useRoute();
  const brandId = parseInt(route.params.brandId as string);

  return brandId;
}
