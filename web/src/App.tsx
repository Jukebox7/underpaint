import { useCallback, useEffect, useRef, useState } from 'react'
import Dropzone from './components/Dropzone'
import ResultGallery from './components/ResultGallery'
import PalettePanel from './components/PalettePanel'
import { processImage, type ProcessOptions, type ProcessResponse } from './api'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [original, setOriginal] = useState<string | null>(null)
  const [result, setResult] = useState<ProcessResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [numColors, setNumColors] = useState(12)
  const [numPlanes, setNumPlanes] = useState(4)
  const [detail, setDetail] = useState(50)

  // Une seule requête à la fois : si un réglage change pendant l'analyse, on mémorise
  // la demande et on la rejoue dès que la requête en cours se termine.
  const busyRef = useRef(false)
  const pendingRef = useRef<{ file: File; options: ProcessOptions } | null>(null)

  const launch = useCallback(async (f: File, options: ProcessOptions) => {
    if (busyRef.current) {
      pendingRef.current = { file: f, options }
      return
    }
    busyRef.current = true
    setLoading(true)
    setError(null)
    try {
      const res = await processImage(f, options)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur inconnue')
    } finally {
      busyRef.current = false
      const next = pendingRef.current
      pendingRef.current = null
      if (next) {
        void launch(next.file, next.options)
      } else {
        setLoading(false)
      }
    }
  }, [])

  // Relance l'analyse quand l'image ou un réglage change, avec un court debounce
  // pour attendre la fin du glissement d'un curseur.
  useEffect(() => {
    if (!file) return
    const timer = setTimeout(() => {
      void launch(file, { numColors, numPlanes, detail })
    }, 400)
    return () => clearTimeout(timer)
  }, [file, numColors, numPlanes, detail, launch])

  function handleFile(f: File) {
    setResult(null)
    setError(null)
    setOriginal((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(f)
    })
    setFile(f)
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
            onChange={(e) => setDetail(Number(e.target.value))}
          />
        </label>
      </div>

      <Dropzone onFile={handleFile} compact={Boolean(file)} fileName={file?.name} />

      {loading && (
        <p className="status">{result ? 'Mise à jour des réglages…' : 'Analyse en cours…'}</p>
      )}
      {error && <p className="status status--error">{error}</p>}

      {original && result && (
        <div className={`results${loading ? ' results--loading' : ''}`}>
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
