import { defineStore } from "pinia";
import type { Country, Income } from "@/services/projects/AudienceApi";

interface ManualForm {
  name: string;
  gender: string;
  age_min: number | null;
  age_max: number | null;
  income_level: Income | null;
  interests: string[];
  location: Country[];
  saved: boolean;
}

interface FileForm {
  description: string;
  files: File[];
  saved: boolean;
}

interface AudienceFormState {
  createManualForm: ManualForm;
  createWithFileForm: FileForm;
}

export const createAudienceStore = defineStore("audienceForm", {
  state: (): AudienceFormState => ({
    createManualForm: {
      name: "",
      gender: "",
      age_min: null,
      age_max: null,
      income_level: null,
      interests: [],
      location: [],
      saved: false,
    },
    createWithFileForm: {
      description: "",
      files: [],
      saved: false,
    },
  }),

  getters: {
    hasManualFormProgress: (state) => {
      const f = state.createManualForm;

      return Boolean(
        f.name?.trim() ||
          f.gender?.trim() ||
          (typeof f.age_min === "number" && f.age_min > 0) ||
          (typeof f.age_max === "number" && f.age_max > 0) ||
          f.income_level ||
          (Array.isArray(f.interests) && f.interests.length > 0) ||
          (Array.isArray(f.location) && f.location.length > 0),
      );
    },

    hasFileFormProgress: (state) => {
      const f = state.createWithFileForm;

      return Boolean(
        f.description?.trim() || (Array.isArray(f.files) && f.files.length > 0),
      );
    },
  },

  actions: {
    saveManualFormProgress(partial: Partial<ManualForm>) {
      Object.assign(this.createManualForm, partial);
      this.createManualForm.saved = true;
    },

    saveFileFormProgress(partial: Partial<FileForm>) {
      Object.assign(this.createWithFileForm, partial);
      this.createWithFileForm.saved = true;
    },

    resetManualForm() {
      this.createManualForm = {
        name: "",
        gender: "",
        age_min: null,
        age_max: null,
        income_level: null,
        interests: [],
        location: [],
        saved: false,
      };
    },

    resetFileForm() {
      this.createWithFileForm = {
        description: "",
        files: [],
        saved: false,
      };
    },
  },
});
