<script setup lang="ts">
import {
  AdminRoleDetail,
  AdminRoleFunction,
} from "@/services/settings/AdminRolesApi";
import type { PermissionFunctionName } from "@/utils/type-declarations";

const isOpen = defineModel<boolean>({ required: true });
const props = defineProps<{ role: AdminRoleDetail }>();

const defaultSorting: PermissionFunctionName[] = [
  "ADMIN_ORG",
  "ADMIN_USER",
  "ADMIN_ROLES",
  "BRAND",
  "PRODUCT",
  "TARGET_CUSTOMER",
  "PROJECT",
  "UMBRELLA_CAMPAIGN",
  "CAMPAIGN_SETUP",
  "CAMPAIGN_CREATIVE",
  "FUNNEL_FLOW",
  "CAMPAIGN_LAUNCHPAD",
  "APPROVAL_PROCESS",
];

const roleFunctions = computed(() => {
  const defaultFunctions = defaultSorting.map(
    (name) =>
      props.role.functions.find((fn) => fn.name === name) ?? {
        id: 0,
        name,
        long_name: anyCaseToText(name),
        status: "A",
        actions: [],
      },
  );

  const extraFunctions = props.role.functions.filter(
    (fn) => !defaultSorting.includes(fn.name),
  );

  return [...defaultFunctions, ...extraFunctions];
});

const hasAction = (
  roleFunction: AdminRoleFunction,
  action: "C" | "U" | "D" | "R",
) => roleFunction.actions.some((roleAction) => roleAction.id === action);
</script>

<template>
  <Modal v-model="isOpen" :maxWidth="900" closeButton scrollable="inner">
    <ModalHeader>
      {{ $t("settings.roles.modal.view-permissions") }}
    </ModalHeader>

    <ModalBody>
      <div class="tw:mb-7 tw:flex tw:items-center tw:font-medium">
        <span class="tw:text-2xl">{{ role.icon }}</span>
        {{ role.name }}
      </div>

      <h3 class="tw:mb-6 tw:text-xl tw:font-extrabold">
        {{ $t("settings.roles.modal.role-permissions") }}
      </h3>

      <Separator />

      <div class="tw:px-10 tw:py-5">
        <h3 class="tw:text-lg tw:font-bold">
          {{ $t("settings.roles.modal.administrator-access") }}
        </h3>
      </div>

      <Separator />

      <div class="tw:divide-y tw:divide-gray-300">
        <div v-for="roleFunction in roleFunctions">
          <div class="tw:flex tw:justify-between tw:px-10 tw:py-5">
            <p class="tw:text-lg tw:font-medium">
              {{
                $te(`permissions.${roleFunction.name}.title`)
                  ? $t(`permissions.${roleFunction.name}.title`)
                  : roleFunction.long_name
              }}
            </p>
            <div class="tw:flex tw:gap-10">
              <FieldBaseCheckbox
                :label="$t('global.create')"
                disabled
                :modelValue="hasAction(roleFunction, 'C')"
              />
              <FieldBaseCheckbox
                :label="$t('global.read')"
                disabled
                :modelValue="hasAction(roleFunction, 'R')"
              />
              <FieldBaseCheckbox
                :label="$t('global.update')"
                disabled
                :modelValue="hasAction(roleFunction, 'U')"
              />
              <FieldBaseCheckbox
                :label="$t('global.delete')"
                disabled
                :modelValue="hasAction(roleFunction, 'D')"
              />
            </div>
          </div>
        </div>
      </div>
    </ModalBody>

    <ModalFooter>
      <Button variant="outlined" @click="isOpen = false">
        {{ $t("global.cancel") }}
      </Button>

      <Button @click="isOpen = false">
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
