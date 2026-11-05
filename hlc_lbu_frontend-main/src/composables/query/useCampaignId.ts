export default function useCampaignId() {
  const route = useRoute();
  const campaignId = parseInt(route.params.campaignId as string);

  return campaignId;
}
