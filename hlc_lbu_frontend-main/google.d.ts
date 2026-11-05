declare var gapi: any;

declare namespace google {
  namespace accounts {
    namespace oauth2 {
      function initTokenClient(config: {
        client_id: string;
        scope: string;
        callback: (response: any) => void;
      }): {
        requestAccessToken: (options?: { prompt?: string }) => void;
      };
    }
  }

  namespace picker {
    class DocsView {
      setIncludeFolders(val: boolean): DocsView;
      setMimeTypes(val: string): DocsView;
    }

    class PickerBuilder {
      addView(view: DocsView): PickerBuilder;
      setOAuthToken(token: string): PickerBuilder;
      setDeveloperKey(key: string): PickerBuilder;
      setCallback(cb: (data: any) => void): PickerBuilder;
      build(): PickerBuilder;
      setVisible(val: boolean): void;
    }

    enum Action {
      PICKED = "picked",
      CANCEL = "cancel",
    }
  }
}
