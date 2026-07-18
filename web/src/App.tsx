import { useState } from 'react'
import Dropzone from './components/Dropzone'
import ResultGallery from './components/ResultGallery'
import PalettePanel from './components/PalettePanel'
import { processImage, type ProcessResponse } from './api'

export default function App() {
  const [original, setOriginal] = useState<string | null>(null)
  const [result, setResult] = useState<ProcessResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [numColors, setNumColors] = useState(12)
  const [numPlanes, setNumPlanes] = useState(4)
  const [detail, setDetail] = useState(50)

  async function handleFile(file: File) {
    setError(null)
    setResult(null)
    setOriginal(URL.createObjectURL(file))
    setLoading(true)
    try {
      const res = await processImage(file, { numColors, numPlanes, detail })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur inconnue')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>painting</h1>
        <p>Dépose une image — récupère quoi peindre, dans quel ordre, avec quelles couleurs.</p>
      </header>

      <div className="options">
        <label>
          Couleurs : {numColors}
          <input
            type="range"
            min={4}
            max={24}
            value={numColors}
            disabled={loading}
            onChange={(e) => setNumColors(Number(e.target.value))}
          />
        </label>
        <label>
          Plans : {numPlanes}
          <input
            type="range"
            min={2}
            max={8}
            value={numPlanes}
            disabled={loading}
            onChange={(e) => setNumPlanes(Number(e.target.value))}
          />
        </label>
        <label>
          Détail du trait : {detail} {detail >= 100 ? '(brut, sans lissage)' : ''}
          <input
            type="range"
            min={0}
            max={100}
            value={detail}
            disabled={loading}
            onChange={(e) => setDetail(Number(e.target.value))}
          />
        </label>
      </div>

      <Dropzone onFile={handleFile} disabled={loading} />

      {loading && <p className="status">Analyse en cours…</p>}
      {error && <p className="status status--error">{error}</p>}

      {original && result && !loading && (
        <div className="results">
          <ResultGallery original={original} result={result} />
          <PalettePanel
            palette={result.palette}
            planes={result.planes}
            sceneDescription={result.sceneDescription}
            sceneObjects={result.sceneObjects}
          />
        </div>
      )}
    </div>
  )
}
