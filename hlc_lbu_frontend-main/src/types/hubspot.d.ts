declare global {
  interface Window {
    HubSpotConversations?: {
      widget: {
        load: () => void;
        open: () => void;
        refresh: () => void;
      };
    };
    hsConversationsSettings?: {
      loadImmediately?: boolean;
      identificationToken?: string;
      identificationEmail?: string;
    };
    _hsq?: unknown[];
  }
}

export {};
