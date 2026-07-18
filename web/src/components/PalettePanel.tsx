import type { PaletteColor, PlaneInfo, SceneObject } from '../api'

interface Props {
  palette: PaletteColor[]
  planes: PlaneInfo[]
  sceneDescription: string
  sceneObjects: SceneObject[]
}

function recipeText(color: PaletteColor): string {
  return color.recipe.parts
    .map((p) => `${p.parts} × ${p.primary}`)
    .join(' + ')
}

/** Couleur de texte lisible (noir/blanc) sur un fond hex donné. */
function textOn(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return 0.299 * r + 0.587 * g + 0.114 * b > 145 ? '#23242a' : '#fff'
}

function Swatch({ hex, num }: { hex: string; num?: number }) {
  return (
    <span className="swatch" style={{ background: hex, color: textOn(hex) }}>
      {num}
    </span>
  )
}

/** « plan 3 » tel quel ; « arrière-plan (plan 1) » pour les libellés nommés. */
function planeText(planeLabel: string, plane: number): string {
  return planeLabel === `plan ${plane}` ? planeLabel : `${planeLabel} (plan ${plane})`
}

export default function PalettePanel({
  palette,
  planes,
  sceneDescription,
  sceneObjects,
}: Props) {
  return (
    <div className="panel">
      {(sceneDescription || sceneObjects.length > 0) && (
        <section>
          <h2>Ce que voit l'IA</h2>
          {sceneDescription && (
            <p className="scene__desc">{sceneDescription}</p>
          )}
          <ol className="planes">
            {sceneObjects.map((o) => (
              <li key={o.index} className="plane">
                <Swatch hex={o.baseColor} num={o.index} />
                <span className="plane__label">
                  {o.label}{' '}
                  <span className="color__pct">
                    — {planeText(o.planeLabel, o.plane)}
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section>
        <h2>Ordre de peinture</h2>
        <ol className="planes">
          {planes.map((p) => (
            <li key={p.order} className="plane">
              <Swatch hex={p.baseColor} num={p.order} />
              <span className="plane__label">
                {p.label} — fond <span className="color__hex">{p.baseColor}</span>{' '}
                <span className="color__pct">(couleur n°{p.baseColorIndex})</span>
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2>Palette & mélanges acryliques</h2>
        <ul className="colors">
          {palette.map((c) => (
            <li key={c.index} className="color">
              <Swatch hex={c.hex} num={c.index} />
              <span className="color__meta">
                <strong className="color__hex">{c.hex}</strong>{' '}
                <span className="color__pct">({c.pct}%)</span>
                <br />
                <span className="color__recipe">
                  {recipeText(c)} <em>(ΔE {c.recipe.deltaE})</em>
                </span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
