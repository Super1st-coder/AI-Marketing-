export default function useProductId() {
  const route = useRoute();
  const produtId = route.params.productId as string;

  return parseInt(produtId);
}
