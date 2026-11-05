/** When enabled, Funnel Flow home redirects to the paid social flow for campaigns with that channel group. */
export const FUNNEL_FLOW_HOME_AUTO_REDIRECT_TO_PAID_SOCIAL = true;

export function shouldAutoRedirectFromFunnelFlowHome(
  channelGroups: { name: string }[],
): boolean {
  return (
    FUNNEL_FLOW_HOME_AUTO_REDIRECT_TO_PAID_SOCIAL &&
    channelGroups.some(
      (channelGroup) =>
        channelGroup.name === PAID_SOCIAL_CHANNEL_GROUP_NAME &&
        getGroupChannelStyles(channelGroup.name).availableInFunnelFlow,
    )
  );
}
