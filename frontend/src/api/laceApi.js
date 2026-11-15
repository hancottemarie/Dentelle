const API_BASE = "/api";

export async function fetchStitchesCatalog() {
  const res = await fetch(`${API_BASE}/stitches`);
  if (!res.ok) throw new Error("Impossible de charger le catalogue des points.");
  const data = await res.json();
  return data.stitches;
}

export async function uploadImage(file, targetWidthMm) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_width_mm", String(targetWidthMm));

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur lors de l'analyse de l'image.");
  }
  return res.json();
}

export async function generatePattern(params, targetWidthMm) {
  const res = await fetch(
    `${API_BASE}/generate?target_width_mm=${encodeURIComponent(targetWidthMm)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur de génération du patron.");
  }
  return res.json();
}

export async function downloadExportFile(format, params, targetWidthMm) {
  const endpoint = format === "pdf" ? "export/pdf" : "export/svg";
  const res = await fetch(
    `${API_BASE}/${endpoint}?target_width_mm=${encodeURIComponent(targetWidthMm)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...params,
        title: "Carton Technique - Dentelle aux Fuseaux",
      }),
    }
  );
  if (!res.ok) throw new Error(`Échec de l'export ${format.toUpperCase()}.`);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `carton_dentelle_1_1.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
