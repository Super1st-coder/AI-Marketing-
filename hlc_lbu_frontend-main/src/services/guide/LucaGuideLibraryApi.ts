import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";

export type LucaGuideLibraryProduct = {
  id: string;
  name: string;
  brand_name: string;
  category: string;
  description: string | null;
  key_features: string[];
  created_at: string;
};

export type LucaGuideLibraryPersona = {
  id: string;
  name: string;
  age_range: string;
  location: string;
  income_range: string;
  psychographics: string | null;
  motivations: string[];
  challenges: string[];
  created_at: string;
};

export type LucaGuideLibraryProject = {
  id: string;
  name: string;
  description: string | null;
  goal_summary: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
};

export type LucaGuideLibraryUmbrellaCampaign = {
  id: string;
  name: string;
  description: string | null;
  project_id: string;
  product_id: string;
  buyer_persona_id: string;
  period_label: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
};

// HLG-120: the 5th element's picker options — Builder campaigns for a Project. `id` is the Builder
// campaign id (stored as linked_campaign_id); `eligible` is false until its Builder Summary is saved.
export type LucaGuideLibraryCampaign = {
  id: string;
  name: string;
  eligible: boolean;
  // Resolved LOCAL ancestry (present on the brand-wide list) so picking a campaign auto-fills the
  // whole chain. null when the campaign's umbrella isn't synced yet → user links manually.
  umbrella_id: string | null;
  project_id?: string | null;
  product_id?: string | null;
  persona_id?: string | null;
};

export default {
  async listProducts(): Promise<LucaGuideLibraryProduct[]> {
    try {
      return await $lucaGuideApi<LucaGuideLibraryProduct[]>(
        "/api/v2/library/products",
        { method: "GET" },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async listPersonas(): Promise<LucaGuideLibraryPersona[]> {
    try {
      return await $lucaGuideApi<LucaGuideLibraryPersona[]>(
        "/api/v2/library/personas",
        { method: "GET" },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async listProjects(): Promise<LucaGuideLibraryProject[]> {
    try {
      return await $lucaGuideApi<LucaGuideLibraryProject[]>(
        "/api/v2/library/projects",
        { method: "GET" },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async listUmbrellaCampaigns(): Promise<LucaGuideLibraryUmbrellaCampaign[]> {
    try {
      return await $lucaGuideApi<LucaGuideLibraryUmbrellaCampaign[]>(
        "/api/v2/library/umbrella-campaigns",
        { method: "GET" },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // HLG-120 / Marco #14-C: the 5th element. With no projectId → EVERY campaign in the brand, each
  // carrying its resolved LOCAL ancestry so picking one auto-fills the chain. With a projectId →
  // the legacy project-scoped list. Builder campaigns are listed live (the linked value is the
  // Builder campaign id, not a local library row).
  async listCampaigns(projectId?: string): Promise<LucaGuideLibraryCampaign[]> {
    try {
      return await $lucaGuideApi<LucaGuideLibraryCampaign[]>(
        "/api/v2/library/campaigns",
        {
          method: "GET",
          query: projectId ? { project_id: projectId } : {},
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
