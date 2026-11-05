export function getFilenameFromContentDisposition(
  header: string | null,
): string | undefined {
  if (!header) {
    return undefined;
  }

  const utf8Match = header.match(/filename\*=(?:UTF-8'')?([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].replace(/['"]/g, "").trim());
  }

  const match = header.match(/filename="?([^";]+)"?/i);
  return match?.[1]?.trim();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(blobUrl);
}
