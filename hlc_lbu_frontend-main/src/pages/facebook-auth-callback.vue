<script setup>
import { onMounted } from "vue";

usePageTitle();

onMounted(() => {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");

  if (window.location.origin && code) {
    $api(`/v2/external/facebook/auth/${code}`).then((data) => {
      console.log("Access Token:", data.access_token);
      console.log("Expires In:", data.expires_in);

      if (data.access_token) {
        const fakeToken =
          "FAKE_TOKEN_" + Math.random().toString(36).substring(2);
        localStorage.setItem("fb_access_token", fakeToken);
        window.close();
      }

      window.close();
    });
  }
});
</script>

<template>
  <div>{{ $t("facebook-auth-callback.authenticating") }}</div>
</template>
