import { Library, Loader } from "@googlemaps/js-api-loader";

let loaderPromise: Promise<typeof google> | null = null;

export default function useGoogleMaps(libraries: Library[] = ["places"]) {
  if (!loaderPromise) {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as
      | string
      | undefined;
    if (!apiKey) {
      throw new Error("Falta VITE_GOOGLE_MAPS_API_KEY en .env");
    }
    const loader = new Loader({ apiKey, libraries });
    loaderPromise = loader.load().then(() => window.google);
  }
  return loaderPromise;
}
