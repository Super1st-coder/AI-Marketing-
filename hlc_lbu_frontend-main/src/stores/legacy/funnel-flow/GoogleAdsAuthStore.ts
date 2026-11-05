import { defineStore } from "pinia";
import imagenLibraryApi, {
  GoogleDriveImage,
} from "@/services/ImagenLibraryApi";

type OAuthMessage = {
  provider: "google-drive";
  type: "oauth-callback";
  status: "success" | "error";
  code?: string;
  state?: string;
  error?: string;
};

function openPopup(url: string, title = "Google Drive", w = 500, h = 700) {
  const y = window.top?.outerHeight
    ? Math.max((window.top!.outerHeight - h) / 2, 0)
    : 0;
  const x = window.top?.outerWidth
    ? Math.max((window.top!.outerWidth - w) / 2, 0)
    : 0;
  return window.open(
    url,
    title,
    `width=${w},height=${h},left=${x},top=${y},resizable,scrollbars`,
  );
}

let popupRef: Window | null = null;

export const googleAdsAuthStore = defineStore("googleAdsAuth", {
  state: () => ({
    isLinked: false as boolean,
    isLinking: false as boolean,
    error: null as string | null,
    state: null as string | null,
    intervalId: null as number | null,
    images: [] as GoogleDriveImage[],
    searchQuery: "" as string,
    sortBy: "name" as "name" | "createdTime",
    sortDirection: "asc" as "asc" | "desc",
  }),
  getters: {
    filteredImages(state) {
      let imgs = [...state.images];

      if (state.searchQuery) {
        imgs = imgs.filter((img) =>
          img.name.toLowerCase().includes(state.searchQuery.toLowerCase()),
        );
      }

      imgs.sort((a, b) => {
        const dir = state.sortDirection === "asc" ? 1 : -1;

        if (state.sortBy === "name") {
          return a.name.localeCompare(b.name) * dir;
        }
        if (state.sortBy === "createdTime") {
          return (
            (new Date(a.createdTime || "").getTime() -
              new Date(b.createdTime || "").getTime()) *
            dir
          );
        }
        return 0;
      });

      return imgs;
    },
  },
  actions: {
    async startLinking(userEmail: string | null): Promise<boolean> {
      if (this.isLinking) return false;

      return new Promise<boolean>((resolve) => {
        this.error = null;
        this.state = userEmail;

        const callbackUrl = `${window.location.origin}/oauth/callback/google-drive`;
        const baseApi = import.meta.env.VITE_API_BASE_URL;

        const authorizeUrl = `${baseApi}/v2/external/google-ads/auth/${userEmail}?state=${userEmail}&redirect_uri=${encodeURIComponent(callbackUrl)}`;

        popupRef = openPopup(authorizeUrl);
        this.isLinking = true;

        const cleanUp = (result: boolean) => {
          this.isLinking = false;
          this.state = null;
          try {
            popupRef?.close();
          } catch (e: unknown) {
            console.error(e);
          }
          popupRef = null;

          resolve(result);
        };

        const onMessage = async (event: MessageEvent<OAuthMessage>) => {
          const msg = event.data;
          if (!msg) return;
          if (msg.provider !== "google-drive" || msg.type !== "oauth-callback")
            return;
          if (msg.state !== this.state) return;

          window.removeEventListener("message", onMessage);
          clearInterval(this.intervalId!);

          if (msg.status === "success" && msg.code) {
            this.isLinked = true;
            this.error = null;
            cleanUp(true);
          } else {
            this.error = msg.error || "Autorización fallida";
            this.isLinked = false;
            cleanUp(false);
          }
        };

        window.addEventListener("message", onMessage);

        this.intervalId = window.setInterval(() => {
          if (!popupRef || popupRef.closed) {
            clearInterval(this.intervalId!);
            window.removeEventListener("message", onMessage);

            if (this.isLinking) {
              this.error =
                this.error ?? "Popup cerrado antes de completar la vinculación";
              this.isLinked = false;
              cleanUp(false);
            }
          }
        }, 500);
      });
    },

    async fetchImages(userEmail: string, force = false) {
      if (!force && this.images.length) {
        return this.images;
      }
      const data = await imagenLibraryApi.fetchGoogleDriveImages(userEmail);
      this.images = data.files.map((file: GoogleDriveImage) => {
        return {
          ...file,
          folderId: data.folder_id,
        };
      });
      return this.images;
    },
    setSearch(query: string) {
      this.searchQuery = query;
    },
    setSort(by: "name" | "createdTime", direction: "asc" | "desc") {
      this.sortBy = by;
      this.sortDirection = direction;
    },
    async checkLinked() {
      return new Promise<boolean>((resolve) => {
        setTimeout(() => {
          resolve(this.isLinked);
        }, 500);
      });
    },
  },
});
