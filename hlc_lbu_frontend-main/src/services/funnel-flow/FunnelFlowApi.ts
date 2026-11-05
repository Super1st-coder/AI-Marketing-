import { handleCommonErrors } from "../common-errors";

export type FunnelFlow = {
  id: number;
  channel_group_description: string;
  channel_group_id: number;
  channel_group_metrics: [];
  channel_group_name: string;
  channel_group_type: string;
};

export type FunnelFlowListByCampaignResponse = BaseApiResponseData<{
  campaign_id: number;
  funnel_flows: FunnelFlow[];
}>;

export type FunnelFlowChannel = {
  id: number;
  name: string;
  description: string;
  active: boolean;
};

export type FunnelFlowChannelListByFunnelFlowResponse = BaseApiResponseData<{
  brand_id: number;
  campaign_id: number;
  funnel_flow_id: number;
  channels: FunnelFlowChannel[];
}>;

export type SaveChannelsBody = {
  brand_id: number;
  campaign_id: number;
  funnel_flow_id: number;
  channels: {
    id: number;
    selected: boolean;
  }[];
};

export default {
  async getFunnelFlowListByCampaign(
    brand_id: number,
    campaign_id: number,
  ): Promise<FunnelFlowListByCampaignResponse> {
    try {
      return await $api<FunnelFlowListByCampaignResponse>(
        `v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/funnel_flow`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getChannelsByChannelGroup(
    channel_group_id: number,
  ): Promise<BaseApiResponseData<FunnelFlowChannel[]>> {
    try {
      return await $api<BaseApiResponseData<FunnelFlowChannel[]>>(
        `v2/application/hiluca/channel_group/${channel_group_id}/channels`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getChannelsByFunnelFlow(
    brand_id: number,
    campaign_id: number,
    funnel_flow_id: number,
  ): Promise<FunnelFlowChannelListByFunnelFlowResponse> {
    try {
      return await $api<FunnelFlowChannelListByFunnelFlowResponse>(
        `v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/funnel_flow/${funnel_flow_id}/channels`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveChannelsByFunnelFlow(
    body: SaveChannelsBody,
  ): Promise<BaseApiResponseData<FunnelFlowChannel[]>> {
    try {
      return await $api<BaseApiResponseData<FunnelFlowChannel[]>>(
        `v2/application/hiluca/brand/funnel_flow/set_channels`,
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
