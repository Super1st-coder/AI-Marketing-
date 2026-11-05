export default function useBuyerPersonId() {
  const route = useRoute();
  const buyerPersonId = parseInt(route.params.buyerPersonId as string);

  return buyerPersonId;
}
