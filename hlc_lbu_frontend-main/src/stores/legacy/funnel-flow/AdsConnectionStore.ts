import { defineStore } from "pinia";

export type Connection = "google-ads" | "meta-ads" | "";

export const adsConnectionStore = defineStore("adsConnection", {
  state: () => ({
    connection: "" as Connection,
  }),

  actions: {
    setConnection(connection: Connection) {
      this.connection = connection;
    },
  },
});
