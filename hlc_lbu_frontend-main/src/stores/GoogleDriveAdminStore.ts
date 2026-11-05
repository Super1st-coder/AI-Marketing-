import { defineStore } from "pinia";

export const googleDriveAdminStore = defineStore("googleDriveAdmin", {
  state: () => ({
    accessToken: "" as string | null,
    expiresAt: null as number | null,
    lastFile: null as any | null,
  }),
  actions: {
    setToken(token: string, expiresAt: number) {
      this.accessToken = token;
      this.expiresAt = expiresAt;
      localStorage.setItem("gdrive_token", token);
      localStorage.setItem("gdrive_expires_at", expiresAt.toString());
    },
    loadToken() {
      this.accessToken = localStorage.getItem("gdrive_token");
      const expires = localStorage.getItem("gdrive_expires_at");
      this.expiresAt = expires ? parseInt(expires, 10) : null;
    },
    isTokenExpired() {
      return !this.expiresAt || Date.now() >= this.expiresAt;
    },
    setLastFile(file: any) {
      this.lastFile = file;
      localStorage.setItem("gdrive_last_file", JSON.stringify(file));
    },
    loadLastFile() {
      const file = localStorage.getItem("gdrive_last_file");
      if (file) {
        this.lastFile = JSON.parse(file);
      }
    },
  },
});
