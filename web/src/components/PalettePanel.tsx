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
                <span className="swatch" style={{ background: o.baseColor }} />
                <span className="plane__label">
                  {o.index}. {o.label}{' '}
                  <span className="color__pct">
                    — {o.planeLabel} (plan {o.plane})
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
              <span className="swatch" style={{ background: p.baseColor }} />
              <span className="plane__label">
                {p.label} — fond {p.baseColor}{' '}
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
              <span className="swatch" style={{ background: c.hex }} />
              <span className="color__meta">
                <strong>
                  {c.index}. {c.hex}
                </strong>{' '}
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
