<template>
  <div class="p-8 text-gray-900">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold">Facebook Service Test Page</h1>
      <div class="flex items-center gap-4">
        <template v-if="authenticated.is_valid">
          <span
            class="rounded-full border border-green-200 bg-green-100 px-3 py-1 text-sm font-medium text-green-700"
          >
            Meta Connected
          </span>
          <button
            @click="disconnectFacebook"
            class="rounded bg-red-600 px-4 py-2 font-medium text-white transition hover:bg-red-700"
          >
            Disconnect
          </button>
        </template>
        <button
          v-else
          @click="authWithFacebook"
          class="rounded bg-orange-600 px-4 py-2 font-medium text-white transition hover:bg-orange-700"
        >
          Connect with Meta
        </button>
      </div>
    </div>

    <div
      v-if="authenticated.is_valid && authenticated.raw?.data?.scopes"
      class="mb-6 rounded border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700"
    >
      <strong>Authorized Scopes:</strong>
      <div class="mt-2 flex flex-wrap gap-2">
        <span
          v-for="scope in authenticated.raw.data.scopes"
          :key="scope"
          class="rounded-md bg-gray-200 px-2 py-0.5 font-mono text-xs text-gray-800"
        >
          {{ scope }}
        </span>
      </div>
    </div>

    <!-- Ad Accounts Section -->
    <div class="mb-8">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-xl font-semibold">Ad Accounts</h2>
        <button
          @click="fetchAdAccounts"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
          :disabled="loadingAccounts"
        >
          {{ loadingAccounts ? "Loading..." : "Fetch Ad Accounts" }}
        </button>
      </div>

      <div
        v-if="errorAccounts"
        class="mb-4 rounded bg-red-100 p-4 text-red-700"
      >
        {{ errorAccounts }}
      </div>

      <div
        v-if="adAccounts.length > 0"
        class="overflow-hidden rounded bg-white shadow"
      >
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
              >
                Name
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
              >
                Account ID
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
              >
                ID
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
              >
                Currency
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 bg-white">
            <tr v-for="account in adAccounts" :key="account.id">
              <td class="px-6 py-4 whitespace-nowrap">{{ account.name }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                {{ account.account_id }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">{{ account.id }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                {{ account.currency }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        v-else-if="!loadingAccounts && accountsFetched"
        class="text-gray-500 italic"
      >
        No ad accounts found.
      </div>
    </div>

    <!-- Pages Section -->
    <div class="mb-8">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-xl font-semibold">Facebook Pages</h2>
        <button
          @click="fetchPages"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
          :disabled="loadingPages"
        >
          {{ loadingPages ? "Loading..." : "Fetch Pages" }}
        </button>
      </div>

      <div v-if="errorPages" class="mb-4 rounded bg-red-100 p-4 text-red-700">
        {{ errorPages }}
      </div>

      <div
        v-if="pages.length > 0"
        class="overflow-hidden rounded bg-white shadow"
      >
        <ul class="divide-y divide-gray-200">
          <li v-for="page in pages" :key="page.id" class="px-6 py-4">
            <span class="font-medium">{{ page.name }}</span>
            <span class="ml-2 text-sm text-gray-500">(ID: {{ page.id }})</span>
          </li>
        </ul>
      </div>
      <div
        v-else-if="!loadingPages && pagesFetched"
        class="text-gray-500 italic"
      >
        No pages found.
      </div>
    </div>

    <!-- Page Assets Section -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">
        Page Assets (Leadgen Forms & WhatsApp Numbers)
      </h2>
      <div class="mb-4 max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="asset-page-id"
          >
            Page ID
          </label>
          <input
            v-model="assetPageId"
            id="asset-page-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Page ID"
          />
        </div>
        <div class="flex gap-4">
          <button
            @click="fetchPageLeadgenForms"
            class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
            :disabled="loadingAssetForms || !assetPageId"
          >
            {{ loadingAssetForms ? "Fetching..." : "Fetch Leadgen Forms" }}
          </button>
          <button
            @click="fetchPageWhatsAppNumbers"
            class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
            :disabled="loadingAssetWhatsApp || !assetPageId"
          >
            {{
              loadingAssetWhatsApp ? "Fetching..." : "Fetch WhatsApp Numbers"
            }}
          </button>
          <button
            @click="fetchPageAdsPosts"
            class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
            :disabled="loadingAssetAdsPosts || !assetPageId"
          >
            {{
              loadingAssetAdsPosts
                ? "Fetching..."
                : "Test pages_manage_ads (Fetch Ads Posts)"
            }}
          </button>
        </div>
      </div>

      <div
        v-if="assetFormsError"
        class="mb-4 rounded bg-red-100 p-4 text-red-700"
      >
        {{ assetFormsError }}
      </div>

      <div v-if="leadgenForms.length > 0" class="mb-4">
        <h3 class="mb-2 font-semibold">Leadgen Forms:</h3>
        <ul class="divide-y divide-gray-200 rounded bg-white p-4 shadow">
          <li v-for="form in leadgenForms" :key="form.id" class="py-2">
            <span class="font-medium">{{ form.name }}</span>
            <span class="ml-2 text-sm text-gray-500"
              >(ID: {{ form.id }}, Status: {{ form.status }})</span
            >
          </li>
        </ul>
      </div>

      <div v-if="whatsappNumbers.length > 0" class="mb-4">
        <h3 class="mb-2 font-semibold">WhatsApp Numbers:</h3>
        <ul class="divide-y divide-gray-200 rounded bg-white p-4 shadow">
          <li v-for="num in whatsappNumbers" :key="num.id" class="py-2">
            <span class="font-medium">{{ num.display_phone_number }}</span>
            <span class="ml-2 text-sm text-gray-500"
              >(ID: {{ num.id }}, Name: {{ num.verified_name }})</span
            >
          </li>
        </ul>
      </div>

      <div v-if="adsPosts.length > 0">
        <h3 class="mb-2 font-semibold">Ads Posts (pages_manage_ads Test):</h3>
        <ul class="divide-y divide-gray-200 rounded bg-white p-4 shadow">
          <li v-for="post in adsPosts" :key="post.id" class="py-2">
            <span class="font-medium">{{
              post.message || post.name || "Untitled Post"
            }}</span>
            <span class="ml-2 text-sm text-gray-500"
              >(ID: {{ post.id }}, Story ID: {{ post.story_id }})</span
            >
          </li>
        </ul>
      </div>
    </div>

    <!-- Test Upload Section -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Test Creative Upload</h2>
      <div class="max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="ad-account-id"
          >
            Ad Account ID (Optional)
          </label>
          <input
            v-model="adAccountId"
            id="ad-account-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Ad Account ID"
          />
        </div>

        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="page-id"
          >
            Page ID (Optional)
          </label>
          <input
            v-model="pageId"
            id="page-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Page ID"
          />
        </div>

        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="campaign-id"
          >
            Campaign ID
          </label>
          <input
            v-model="campaignId"
            id="campaign-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Campaign ID"
          />
        </div>

        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="test-objective"
          >
            Objective (e.g. OUTCOME_LEADS, OUTCOME_TRAFFIC)
          </label>
          <input
            v-model="testObjective"
            id="test-objective"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Objective"
          />
        </div>

        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="test-opt-goal"
          >
            Optimization Goal (e.g. LEAD_GENERATION, REACH)
          </label>
          <input
            v-model="testOptGoal"
            id="test-opt-goal"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Optimization Goal"
          />
        </div>

        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="test-form-id"
          >
            Lead Gen Form ID (Optional)
          </label>
          <input
            v-model="testFormId"
            id="test-form-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Lead Gen Form ID"
          />
        </div>

        <button
          @click="startUpload"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
          :disabled="loadingUpload || !campaignId"
        >
          {{ loadingUpload ? "Uploading..." : "Upload Creatives" }}
        </button>
      </div>

      <div v-if="uploadResult" class="mt-4">
        <h3 class="mb-2 font-semibold">Result:</h3>
        <pre class="max-h-96 overflow-auto rounded bg-gray-100 p-4 text-sm">{{
          JSON.stringify(uploadResult, null, 2)
        }}</pre>
      </div>

      <div v-if="errorUpload" class="mt-4 rounded bg-red-100 p-4 text-red-700">
        <p class="font-bold">Error:</p>
        <pre class="whitespace-pre-wrap">{{ errorUpload }}</pre>
      </div>
    </div>

    <!-- Ads list -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Fetch Ads List</h2>
      <div>
        <ul>
          <li v-for="ad in adsList" :key="ad.id" class="tw:mb-4">
            <ul class="tw:list-disc">
              <li><strong>ID:</strong> {{ ad.id }}</li>
              <li><strong>Name:</strong> {{ ad.name }}</li>
              <li>
                <span>Creative</span>
                <ul>
                  <li>ID: {{ ad.creative?.id }}</li>
                  <li>Name: {{ ad.creative?.name }}</li>
                </ul>
              </li>
              <li>
                <button
                  @click="openInsightsByAdModal(ad.id)"
                  class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
                >
                  Insights
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      <div class="max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="ad-account-id"
          >
            Ad Account ID (Optional)
          </label>
          <input
            v-model="adAccountId"
            id="ad-account-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Ad Account ID"
          />
        </div>

        <button
          @click="fetchAdsList"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
        >
          {{ loadingUpload ? "Uploading..." : "Upload Ads" }}
        </button>
      </div>
    </div>

    <!-- Adsets list -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Fetch Adsets List</h2>
      <div>
        <ul>
          <li v-for="ad in adsetsList" :key="ad.id" class="tw:mb-4">
            <ul class="tw:list-disc">
              <li><strong>ID:</strong> {{ ad.id }}</li>
              <li><strong>Name:</strong> {{ ad.name }}</li>
              <li>
                <button
                  @click="openInsightsByAdsetModal(ad.id)"
                  class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
                >
                  Insights
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      <div class="max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="ad-account-id"
          >
            Ad Account ID (Optional)
          </label>
          <input
            v-model="adAccountId"
            id="ad-account-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Ad Account ID"
          />
        </div>

        <button
          @click="fetchAdsetsList"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
        >
          {{ loadingUpload ? "Uploading..." : "Upload Adsets" }}
        </button>
      </div>
    </div>

    <!-- Insights by Ad Account -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Fetch Campaigns List</h2>
      <div>
        <ul>
          <li v-for="ad in campaignsList" :key="ad.id" class="tw:mb-4">
            <ul class="tw:list-disc">
              <li><strong>ID:</strong> {{ ad.id }}</li>
              <li><strong>Name:</strong> {{ ad.name }}</li>
              <li>
                <button
                  @click="openInsightsByCampaignModal(ad.id)"
                  class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
                >
                  Insights
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      <div class="max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="ad-account-id"
          >
            Ad Account ID (Optional)
          </label>
          <input
            v-model="adAccountId"
            id="ad-account-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Ad Account ID"
          />
        </div>

        <button
          @click="fetchCampaignsList"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
        >
          {{ loadingUpload ? "Uploading..." : "Upload Campaigns" }}
        </button>
      </div>
    </div>

    <!-- Insights by Ad Account -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Fetch Ad Account Insights</h2>
      <div class="max-w-md">
        <div class="mb-4">
          <label
            class="mb-2 block text-sm font-bold text-gray-700"
            for="ad-account-id"
          >
            Ad Account ID (Optional)
          </label>
          <input
            v-model="adAccountId"
            id="ad-account-id"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Ad Account ID"
          />
        </div>

        <button
          @click="openInsightsByAdAccountModal(adAccountId)"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
        >
          Insights by Ad Account
        </button>
      </div>
    </div>

    <!-- Meta Search Test Section -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Test Meta Search</h2>
      <div class="max-w-md">
        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Search Type
          </label>
          <select
            v-model="searchType"
            class="focus:shadow-outline w-full rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
          >
            <option value="adcity">adcity (City)</option>
            <option value="adcountry">adcountry (Country)</option>
            <option value="adcountrystate">adcountrystate (Region)</option>
            <option value="adinterest">adinterest (Interest)</option>
            <option value="adzipcode">adzipcode (Zip Code)</option>
          </select>
        </div>

        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Query (Required)
          </label>
          <input
            v-model="searchQuery"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter search query (e.g. Mexico)"
          />
        </div>

        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Location Types (Comma separated)
          </label>
          <input
            v-model="locationTypes"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="e.g. city, country"
          />
        </div>

        <button
          @click="executeSearchMeta"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
          :disabled="loadingSearch || !searchQuery"
        >
          {{ loadingSearch ? "Searching..." : "Execute Search" }}
        </button>
      </div>

      <div v-if="searchResults" class="mt-4">
        <h3 class="mb-2 font-semibold">Result:</h3>
        <pre class="max-h-96 overflow-auto rounded bg-gray-100 p-4 text-sm">{{
          JSON.stringify(searchResults, null, 2)
        }}</pre>
      </div>

      <div v-if="errorSearch" class="mt-4 rounded bg-red-100 p-4 text-red-700">
        <p class="font-bold">Error:</p>
        <pre class="whitespace-pre-wrap">{{ errorSearch }}</pre>
      </div>
    </div>

    <!-- Strapi Campaign Test Section -->
    <div class="mb-8 border-t pt-8">
      <h2 class="mb-4 text-xl font-semibold">Test Strapi Campaign Fetch</h2>
      <div class="max-w-md">
        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Campaign ID (Required)
          </label>
          <input
            v-model="strapiCampaignId"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Campaign ID"
          />
        </div>

        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Brand ID (Optional)
          </label>
          <input
            v-model="strapiBrandId"
            type="number"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Brand ID"
          />
        </div>

        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            Channel Group ID (Optional)
          </label>
          <input
            v-model="strapiChannelGroupId"
            type="number"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter Channel Group ID"
          />
        </div>

        <div class="mb-4">
          <label class="mb-2 block text-sm font-bold text-gray-700">
            User ID (Optional)
          </label>
          <input
            v-model="strapiUserId"
            type="text"
            class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
            placeholder="Enter User ID"
          />
        </div>

        <button
          @click="fetchStrapiCampaign"
          class="rounded bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:opacity-50"
          :disabled="loadingStrapi || !strapiCampaignId"
        >
          {{ loadingStrapi ? "Fetching..." : "Fetch Campaign Data" }}
        </button>
      </div>

      <div v-if="strapiResult" class="mt-4">
        <h3 class="mb-2 font-semibold">Result:</h3>
        <pre class="max-h-96 overflow-auto rounded bg-gray-100 p-4 text-sm">{{
          JSON.stringify(strapiResult, null, 2)
        }}</pre>
      </div>

      <div v-if="errorStrapi" class="mt-4 rounded bg-red-100 p-4 text-red-700">
        <p class="font-bold">Error:</p>
        <pre class="whitespace-pre-wrap">{{ errorStrapi }}</pre>
      </div>
    </div>
  </div>

  <Modal v-model="showInsightsByAdModal" :maxWidth="1024" closeButton>
    <ModalHeader> Insights for Ad {{ adIdForInsights }}</ModalHeader>

    <ModalBody>
      {{ insightsByAd }}
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        @click="showInsightsByAdModal = false"
      >
        Close
      </Button>
    </ModalFooter>
  </Modal>

  <Modal v-model="showInsightsByAdsetModal" :maxWidth="1024" closeButton>
    <ModalHeader> Insights for Adset</ModalHeader>

    <ModalBody>
      {{ insightsByAdset }}
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        @click="showInsightsByAdModal = false"
      >
        Close
      </Button>
    </ModalFooter>
  </Modal>

  <Modal v-model="showInsightsByCampaignModal" :maxWidth="1024" closeButton>
    <ModalHeader> Insights for Campaign</ModalHeader>

    <ModalBody>
      {{ insightsByCampaign }}
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        @click="showInsightsByAdModal = false"
      >
        Close
      </Button>
    </ModalFooter>
  </Modal>

  <Modal v-model="showInsightsByAdAccountModal" :maxWidth="1024" closeButton>
    <ModalHeader> Insights for Ad Account</ModalHeader>

    <ModalBody>
      {{ insightsByAdAccount }}
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        @click="showInsightsByAdModal = false"
      >
        Close
      </Button>
    </ModalFooter>
  </Modal>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import ChannelConnections, {
  AdAccount,
  AdPage,
} from "@/services/funnel-flow/ChannelConnections";

const authenticated = ref<any>({ is_valid: false });

const APPID = "461281100028116";
const REDIRECTURI = `${window.location.origin}/facebook-auth-callback`;
const SCOPE =
  "email,public_profile,pages_show_list,pages_manage_ads,pages_read_engagement,ads_read,ads_management,business_management,whatsapp_business_management";
const WIDTH = 1024;
const HEIGHT = 780;
const LEFT = window.screenX + (window.outerWidth - WIDTH) / 2;
const TOP = window.screenY + (window.outerHeight - HEIGHT) / 2;

const checkAuthStatus = async () => {
  try {
    const response = await $api("/v2/external/facebook/validate_token");
    authenticated.value = response;
  } catch (err) {
    console.error("Error validating token:", err);
    authenticated.value = { is_valid: false };
  }
};

function authWithFacebook() {
  window.open(
    `https://www.facebook.com/v20.0/dialog/oauth?client_id=${APPID}&redirect_uri=${encodeURIComponent(
      REDIRECTURI,
    )}&scope=${SCOPE}&response_type=code`,
    "facebookLogin",
    `width=${WIDTH},height=${HEIGHT},left=${LEFT},top=${TOP}`,
  );

  const checkToken = setInterval(async () => {
    const token = localStorage.getItem("fb_access_token");
    if (token) {
      clearInterval(checkToken);
      localStorage.removeItem("fb_access_token");
      await checkAuthStatus();
      if (authenticated.value.is_valid) {
        fetchAdAccounts();
        fetchPages();
      }
    }
  }, 500);
}

const disconnectFacebook = async () => {
  try {
    await ChannelConnections.disconnectFacebookToken();
    authenticated.value = { is_valid: false };
    adAccounts.value = [];
    pages.value = [];
    leadgenForms.value = [];
    whatsappNumbers.value = [];
  } catch (err) {
    console.error("Error disconnecting Facebook:", err);
  }
};

onMounted(() => {
  checkAuthStatus();
});

interface Ad {
  id: string;
  name: string;
  creative?: {
    id: string;
    name: string;
  };
}

// Ad Accounts State
const adAccounts = ref<AdAccount[]>([]);
const loadingAccounts = ref(false);
const errorAccounts = ref("");
const accountsFetched = ref(false);

const fetchAdAccounts = async () => {
  console.log("fetchAdAccounts called");
  loadingAccounts.value = true;
  errorAccounts.value = "";
  try {
    const response = await ChannelConnections.getAdAccounts();
    console.log("getAdAccounts response:", response);
    if (response && response.data) {
      adAccounts.value = response.data;
    } else {
      console.warn("Response format unexpected:", response);
    }
  } catch (err: any) {
    console.error("Error fetching ad accounts:", err);
    errorAccounts.value = err.message || "Failed to fetch ad accounts";
  } finally {
    loadingAccounts.value = false;
    accountsFetched.value = true;
  }
};

// Pages State
const pages = ref<AdPage[]>([]);
const loadingPages = ref(false);
const errorPages = ref("");
const pagesFetched = ref(false);

const fetchPages = async () => {
  console.log("fetchPages called");
  loadingPages.value = true;
  errorPages.value = "";
  try {
    const response = await ChannelConnections.getAdPages();
    console.log("getAdPages response:", response);
    if (response && response.data) {
      pages.value = response.data;
    } else {
      console.warn("Response format unexpected:", response);
    }
  } catch (err: any) {
    console.error("Error fetching pages:", err);
    errorPages.value = err.message || "Failed to fetch pages";
  } finally {
    loadingPages.value = false;
    pagesFetched.value = true;
  }
};

// Page Assets State
const assetPageId = ref("");
const leadgenForms = ref<any[]>([]);
const whatsappNumbers = ref<any[]>([]);
const adsPosts = ref<any[]>([]);
const loadingAssetForms = ref(false);
const loadingAssetWhatsApp = ref(false);
const loadingAssetAdsPosts = ref(false);
const assetFormsError = ref("");

const fetchPageLeadgenForms = async () => {
  if (!assetPageId.value) return;
  loadingAssetForms.value = true;
  assetFormsError.value = "";
  leadgenForms.value = [];
  try {
    const response = await ChannelConnections.getLeadgenForms(
      assetPageId.value,
    );
    if (response && response.data) {
      leadgenForms.value = response.data;
    }
  } catch (err: any) {
    console.error("Error fetching leadgen forms:", err);
    assetFormsError.value = err.message || "Failed to fetch leadgen forms";
  } finally {
    loadingAssetForms.value = false;
  }
};

const fetchPageWhatsAppNumbers = async () => {
  if (!assetPageId.value) return;
  loadingAssetWhatsApp.value = true;
  assetFormsError.value = "";
  whatsappNumbers.value = [];
  try {
    const response = await ChannelConnections.getWhatsAppPhoneNumbers(
      assetPageId.value,
    );
    if (response && response.data) {
      whatsappNumbers.value = response.data;
    }
  } catch (err: any) {
    console.error("Error fetching WhatsApp numbers:", err);
    assetFormsError.value = err.message || "Failed to fetch WhatsApp numbers";
  } finally {
    loadingAssetWhatsApp.value = false;
  }
};

const fetchPageAdsPosts = async () => {
  if (!assetPageId.value) return;
  loadingAssetAdsPosts.value = true;
  assetFormsError.value = "";
  adsPosts.value = [];
  try {
    const response = await ChannelConnections.getAdsPosts(assetPageId.value);
    if (response && response.data) {
      adsPosts.value = response.data;
    }
  } catch (err: any) {
    console.error("Error fetching ads posts:", err);
    assetFormsError.value =
      err.message || "Failed to fetch ads posts (pages_manage_ads)";
  } finally {
    loadingAssetAdsPosts.value = false;
  }
};

// Upload State
const campaignId = ref("");
const adAccountId = ref("");
const pageId = ref("");
const testObjective = ref("");
const testOptGoal = ref("");
const testFormId = ref("");
const loadingUpload = ref(false);
const uploadResult = ref<any>(null);
const errorUpload = ref("");

const adsList = ref<Ad[]>([]);
const adsetsList = ref<Ad[]>([]);
const campaignsList = ref<Ad[]>([]);
const insightsByAd = ref<any>(null);
const insightsByAdset = ref<any>(null);
const insightsByCampaign = ref<any>(null);
const insightsByAdAccount = ref<any>(null);
const showInsightsByAdModal = ref(false);
const showInsightsByAdsetModal = ref(false);
const showInsightsByCampaignModal = ref(false);
const showInsightsByAdAccountModal = ref(false);
const adIdForInsights = ref<string | null>(null);

const startUpload = async () => {
  if (!campaignId.value) return;

  loadingUpload.value = true;
  errorUpload.value = "";
  uploadResult.value = null;

  try {
    const response = await ChannelConnections.testUploadCreatives(
      campaignId.value,
      {
        ad_account_id: adAccountId.value,
        page_id: pageId.value,
        objective: testObjective.value,
        optimization_goal: testOptGoal.value,
        lead_gen_form_id: testFormId.value || null,
      },
      "STANDARD",
    );
    uploadResult.value = response;
  } catch (err: any) {
    console.error("Error uploading creatives:", err);
    // Try to extract more detail if available
    const errorDetail = err.data || err.response?._data || err.message;
    errorUpload.value =
      typeof errorDetail === "object"
        ? JSON.stringify(errorDetail, null, 2)
        : String(errorDetail);
  } finally {
    loadingUpload.value = false;
  }
};

// Strapi Test State
const strapiCampaignId = ref("");
const strapiBrandId = ref<number | undefined>();
const strapiChannelGroupId = ref<number | undefined>();
const strapiUserId = ref("");
const loadingStrapi = ref(false);
const strapiResult = ref<any>(null);
const errorStrapi = ref("");

const fetchStrapiCampaign = async () => {
  if (!strapiCampaignId.value) return;

  loadingStrapi.value = true;
  errorStrapi.value = "";
  strapiResult.value = null;

  try {
    const response = await ChannelConnections.testStrapiGetCampaign(
      strapiCampaignId.value,
      strapiBrandId.value,
      strapiChannelGroupId.value,
      strapiUserId.value || undefined,
    );
    strapiResult.value = response;
  } catch (err: any) {
    console.error("Error fetching Strapi campaign:", err);
    const errorDetail = err.data || err.response?._data || err.message;
    errorStrapi.value =
      typeof errorDetail === "object"
        ? JSON.stringify(errorDetail, null, 2)
        : String(errorDetail);
  } finally {
    loadingStrapi.value = false;
  }
};

// Meta Search State
const searchType = ref("adcity");
const searchQuery = ref("");
const locationTypes = ref("city");
const loadingSearch = ref(false);
const searchResults = ref<any>(null);
const errorSearch = ref("");

const executeSearchMeta = async () => {
  if (!searchQuery.value) return;

  loadingSearch.value = true;
  errorSearch.value = "";
  searchResults.value = null;

  try {
    const locTypes = locationTypes.value
      ? locationTypes.value.split(",").map((s) => s.trim())
      : [];
    const response = await ChannelConnections.searchMeta(
      searchType.value,
      searchQuery.value,
      locTypes,
    );
    searchResults.value = response;
  } catch (err: any) {
    console.error("Error searching Meta:", err);
    const errorDetail = err.data || err.response?._data || err.message;
    errorSearch.value =
      typeof errorDetail === "object"
        ? JSON.stringify(errorDetail, null, 2)
        : String(errorDetail);
  } finally {
    loadingSearch.value = false;
  }
};

async function fetchAdsList() {
  const resp = await $api(`/v2/external/facebook/ads/${adAccountId.value}`);
  adsList.value = resp.data;
}

async function fetchAdsetsList() {
  const resp = await $api(`/v2/external/facebook/adsets/${adAccountId.value}`);
  adsetsList.value = resp.data;
}

async function fetchCampaignsList() {
  const resp = await $api(
    `/v2/external/facebook/campaigns/${adAccountId.value}`,
  );
  campaignsList.value = resp.data;
}

async function fetchInsightsByAd(adId: string) {
  const resp = await $api(`/v2/external/facebook/insights/entity/${adId}`, {
    params: {
      fields:
        "impressions,spend,cpc,ctr,clicks,inline_link_clicks,inline_link_click_ctr,frequency,actions",
    },
  });
  insightsByAd.value = resp.data;
}

async function fetchInsightsByAdset(adsetId: string) {
  const resp = await $api(`/v2/external/facebook/insights/entity/${adsetId}`, {
    params: {
      fields:
        "impressions,spend,cpc,ctr,clicks,inline_link_clicks,inline_link_click_ctr,frequency,actions",
    },
  });
  insightsByAdset.value = resp.data;
}

async function fetchInsightsByCampaign(campaignId: string) {
  const resp = await $api(
    `/v2/external/facebook/insights/entity/${campaignId}`,
    {
      params: {
        fields:
          "impressions,spend,cpc,ctr,clicks,inline_link_clicks,inline_link_click_ctr,frequency,actions",
      },
    },
  );
  insightsByCampaign.value = resp.data;
}

async function fetchInsightsByAdAccount(adAccount: string) {
  const resp = await $api(
    `/v2/external/facebook/insights/ad_account/${adAccount}`,
    {
      params: {
        fields:
          "impressions,spend,cpc,ctr,clicks,inline_link_clicks,inline_link_click_ctr,frequency,actions",
      },
    },
  );
  insightsByAdAccount.value = resp.data;
}

async function openInsightsByAdModal(adId: string) {
  adIdForInsights.value = adId;
  await fetchInsightsByAd(adId);
  showInsightsByAdModal.value = true;
}

async function openInsightsByAdsetModal(adsetId: string) {
  await fetchInsightsByAdset(adsetId);
  showInsightsByAdsetModal.value = true;
}

async function openInsightsByCampaignModal(campaignId: string) {
  await fetchInsightsByCampaign(campaignId);
  showInsightsByCampaignModal.value = true;
}

async function openInsightsByAdAccountModal(adAccount: string) {
  await fetchInsightsByAdAccount(adAccount);
  showInsightsByAdAccountModal.value = true;
}
</script>
