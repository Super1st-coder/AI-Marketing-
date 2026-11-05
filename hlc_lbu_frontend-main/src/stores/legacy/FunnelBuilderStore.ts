import { defineStore } from "pinia";

export const useFunnelBuilderStore = defineStore("FunnelBuilderStore", () => {
  const data = ref<
    {
      funnelFramework?: string;
      funnelStage?: string;
      funnelStageType?: string;
    } & Record<string, any>
  >({});

  return {
    data,
  };
});
