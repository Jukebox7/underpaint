// Appel centralisé au backend. Voir docs/05-api/contrat-api.md.

export interface RecipePart {
  primary: string
  parts: number
}

export interface Recipe {
  parts: RecipePart[]
  deltaE: number
}

export interface PaletteColor {
  index: number
  hex: string
  pct: number
  recipe: Recipe
}

export interface PlaneInfo {
  order: number
  baseColor: string
  baseColorIndex: number
  label: string
}

export interface SceneObject {
  index: number
  label: string
  plane: number
  planeLabel: string
  baseColor: string
}

export interface ProcessResponse {
  lineart: string
  sepia: string
  objectContours: string
  objectPlanes: string
  sceneDescription: string
  sceneObjects: SceneObject[]
  planesMap: string
  paintByNumber: string
  palette: PaletteColor[]
  planes: PlaneInfo[]
}

export interface ProcessOptions {
  numColors: number
  numPlanes: number
  detail: number
}

export async function processImage(
  file: File,
  options: ProcessOptions,
): Promise<ProcessResponse> {
  const form = new FormData()
  form.append('image', file)
  form.append('num_colors', String(options.numColors))
  form.append('num_planes', String(options.numPlanes))
  form.append('detail', String(options.detail))

  const res = await fetch('/api/process', { method: 'POST', body: form })
  if (!res.ok) {
    let detail = `Erreur ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // réponse non-JSON : on garde le message par défaut
    }
    throw new Error(detail)
  }
  return (await res.json()) as ProcessResponse
}
