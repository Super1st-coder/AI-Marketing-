import ChannelConnections from "@/services/funnel-flow/ChannelConnections";

const APP_ID = "461281100028116";
const REDIRECT_URI = `${window.location.origin}/facebook-auth-callback`;
const SCOPE =
  "email,public_profile,pages_show_list,pages_manage_ads,pages_read_engagement,ads_read,ads_management,business_management,whatsapp_business_management";
const POPUP_WIDTH = 1024;
const POPUP_HEIGHT = 780;

type UseMetaAdsFacebookAuthOptions = {
  onConnect?: () => Promise<void> | void;
  onDisconnect?: () => Promise<void> | void;
};

export async function useMetaAdsFacebookAuth(
  options: UseMetaAdsFacebookAuthOptions = {},
) {
  const isAuthenticated = ref<boolean>(false);
  const platform = ref("Meta Ads (Facebook & Instagram)");
  const intervalTimeout = ref<ReturnType<typeof setInterval> | undefined>(
    undefined,
  );

  onUnmounted(() => {
    if (intervalTimeout.value) {
      clearInterval(intervalTimeout.value);
    }
  });

  isAuthenticated.value = (
    await ChannelConnections.validateFacebookToken()
  ).is_valid;

  async function handleAfterConnect() {
    isAuthenticated.value = true;
    await options.onConnect?.();
  }

  function handleConnectWithFacebook() {
    const left = window.screenX + (window.outerWidth - POPUP_WIDTH) / 2;
    const top = window.screenY + (window.outerHeight - POPUP_HEIGHT) / 2;

    window.open(
      `https://www.facebook.com/v20.0/dialog/oauth?client_id=${APP_ID}&redirect_uri=${encodeURIComponent(
        REDIRECT_URI,
      )}&scope=${SCOPE}&response_type=code`,
      "facebookLogin",
      `width=${POPUP_WIDTH},height=${POPUP_HEIGHT},left=${left},top=${top}`,
    );

    if (intervalTimeout.value) {
      clearInterval(intervalTimeout.value);
    }

    intervalTimeout.value = setInterval(async () => {
      const token = localStorage.getItem("fb_access_token");

      if (token) {
        clearInterval(intervalTimeout.value);
        localStorage.removeItem("fb_access_token");

        await handleAfterConnect();
      }
    }, 500);
  }

  async function handleDisconnect() {
    await ChannelConnections.disconnectFacebookToken();

    localStorage.removeItem("fb_access_token");
    isAuthenticated.value = false;
    await options.onDisconnect?.();
  }

  return {
    isAuthenticated,
    platform,
    handleConnectWithFacebook,
    handleDisconnect,
  };
}
