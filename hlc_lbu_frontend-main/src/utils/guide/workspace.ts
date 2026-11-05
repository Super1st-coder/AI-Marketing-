function getStorageKey(brandId: number): string {
  return `luca-guide-workspace-id-${brandId}`;
}

export function getLucaGuideWorkspaceId(brandId: number): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return localStorage.getItem(getStorageKey(brandId))?.trim() || undefined;
}

export function setLucaGuideWorkspaceId(brandId: number, workspaceId: string) {
  if (typeof window === "undefined") {
    return;
  }

  const value = workspaceId.trim();
  if (!value) {
    return;
  }

  localStorage.setItem(getStorageKey(brandId), value);
}

export function clearLucaGuideWorkspaceId(brandId: number) {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.removeItem(getStorageKey(brandId));
}
