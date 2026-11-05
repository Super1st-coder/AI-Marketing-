export default function useUmbrellaCampaignId() {
  const route = useRoute();
  const umbrellaCampaignId = parseInt(route.params.umbrellaCampaignId as string);

  return umbrellaCampaignId;
}
