<script setup lang="ts">
interface Props {
  values: {
    campaign_name?: string;
    type?: string;
    bperson?: {
      persona_profile?: string;
      persona_challenges?: string;
      persona_journey?: string;
      persona_motivation?: string;
      image_url?: string | null;
    };
    campaign?: {
      campaign_concept_timing?: string;
      campaign_goals?: string;
      campaign_resources?: string;
      campaign_kpis?: string;
      image_url?: string | null;
    };
    product?: {
      core_incentive_offer?: string;
      problem_solution_fit?: string;
      unique_value_proposition?: string;
      emotional_outcome_payoff?: string;
      image_url?: string | null;
    };
    masters?: Array<{
      title: string;
      horizontal?: string | null;
      square?: string | null;
      vertical?: string | null;
    }>;
  };
}

defineProps<Props>();
</script>

<template>
  <table
    style="
      width: 100%;
      max-width: 600px;
      margin: 0 auto;
      font-family: Arial, sans-serif;
      background-color: #ffffff;
      border-collapse: collapse;
    "
  >
    <tbody>
      <tr>
        <td style="padding: 40px 30px">
          <!-- Header -->
          <table
            style="width: 100%; border-collapse: collapse; margin-bottom: 40px"
          >
            <tbody>
              <tr>
                <td
                  style="
                    text-align: center;
                    padding-bottom: 20px;
                    border-bottom: 2px solid #e5e7eb;
                  "
                >
                  <h1
                    style="
                      color: #111827;
                      font-size: 32px;
                      font-weight: 800;
                      margin: 0;
                      margin-bottom: 10px;
                    "
                  >
                    {{ values?.campaign_name || "Campaign Summary" }}
                  </h1>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Buyer Persona Section -->
          <AssetsEmailSection
            title="Buyer Persona Profile"
            icon="👥"
            headerColor="#FF8811"
            contentBgColor="#FFE7CF"
          >
            <AssetsEmailImageField
              v-if="values?.bperson?.image_url"
              label="Persona Image"
              :imageUrl="values.bperson.image_url"
            />
            <AssetsEmailTextField
              label="Persona Profile"
              :value="values?.bperson?.persona_profile"
            />
            <AssetsEmailTextField
              label="Persona Challenges"
              :value="values?.bperson?.persona_challenges"
            />
            <AssetsEmailTextField
              label="Persona Journey"
              :value="values?.bperson?.persona_journey"
            />
            <AssetsEmailTextField
              label="Persona Motivation"
              :value="values?.bperson?.persona_motivation"
              :isLast="true"
            />
          </AssetsEmailSection>

          <!-- Campaign Details Section -->
          <AssetsEmailSection
            title="Campaign Details"
            icon="📢"
            headerColor="#00BAD1"
            contentBgColor="#00BAD129"
          >
            <AssetsEmailImageField
              v-if="values?.campaign?.image_url"
              label="Campaign Image"
              :imageUrl="values.campaign.image_url"
            />
            <AssetsEmailTextField
              label="Campaign Concept & Timing"
              :value="values?.campaign?.campaign_concept_timing"
            />
            <AssetsEmailTextField
              label="Campaign Goals"
              :value="values?.campaign?.campaign_goals"
            />
            <AssetsEmailTextField
              label="Resources"
              :value="values?.campaign?.campaign_resources"
            />
            <AssetsEmailTextField
              label="Campaign KPIs"
              :value="values?.campaign?.campaign_kpis"
              :isLast="true"
            />
          </AssetsEmailSection>

          <!-- Product Strategy Section -->
          <AssetsEmailSection
            title="Product Strategy"
            icon="🚀"
            headerColor="#29c66f"
            contentBgColor="#28C76F29"
          >
            <AssetsEmailImageField
              v-if="values?.product?.image_url"
              label="Product Image"
              :imageUrl="values.product.image_url"
            />
            <AssetsEmailTextField
              label="Core Incentive / Offer"
              :value="values?.product?.core_incentive_offer"
            />
            <AssetsEmailTextField
              label="Problem/Solution Fit"
              :value="values?.product?.problem_solution_fit"
            />
            <AssetsEmailTextField
              label="Unique Value Proposition"
              :value="values?.product?.unique_value_proposition"
            />
            <AssetsEmailTextField
              label="Emotional Outcome / Payoff"
              :value="values?.product?.emotional_outcome_payoff"
              :isLast="true"
            />
          </AssetsEmailSection>

          <!-- Creative Assets Section -->
          <AssetsEmailSection
            v-if="values?.masters && values?.masters.length > 0"
            title="Creative Assets"
            icon="🎨"
            headerColor="#FF8811"
            contentBgColor="#FFE7CF"
          >
            <tr>
              <td style="padding: 0">
                <template
                  v-for="(master, index) in values?.masters"
                  :key="index"
                >
                  <AssetsEmailMaster
                    v-if="master.horizontal || master.square || master.vertical"
                    :title="master.title || `Master ${index + 1}`"
                  >
                    <AssetsEmailImageField
                      v-if="master.horizontal"
                      label="Horizontal Image"
                      :imageUrl="master.horizontal"
                    />
                    <AssetsEmailImageField
                      v-if="master.square"
                      label="Square Image"
                      :imageUrl="master.square"
                    />
                    <AssetsEmailImageField
                      v-if="master.vertical"
                      label="Vertical Image"
                      :imageUrl="master.vertical"
                    />
                  </AssetsEmailMaster>
                </template>
              </td>
            </tr>
          </AssetsEmailSection>

          <!-- Footer -->
          <table
            style="width: 100%; border-collapse: collapse; margin-top: 40px"
          >
            <tbody>
              <tr>
                <td
                  style="
                    text-align: center;
                    padding-top: 20px;
                    border-top: 2px solid #e5e7eb;
                  "
                >
                  <p style="color: #6b7280; font-size: 14px; margin: 0">
                    Generated on {{ new Date().toLocaleDateString() }} at
                    {{ new Date().toLocaleTimeString() }}
                  </p>
                </td>
              </tr>
            </tbody>
          </table>
        </td>
      </tr>
    </tbody>
  </table>
</template>
