import { useState } from 'react'
import type { ProcessResponse } from '../api'

interface Props {
  original: string
  result: ProcessResponse
}

type TabKey =
  | 'original'
  | 'lineart'
  | 'sepia'
  | 'objectContours'
  | 'objectPlanes'
  | 'planesMap'
  | 'paintByNumber'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'original', label: 'Original' },
  { key: 'lineart', label: 'Dessin au trait' },
  { key: 'sepia', label: 'Sépia' },
  { key: 'objectContours', label: 'Contours par objet' },
  { key: 'objectPlanes', label: 'Objets par plan' },
  { key: 'planesMap', label: 'Carte des plans' },
  { key: 'paintByNumber', label: 'Paint-by-number' },
]

export default function ResultGallery({ original, result }: Props) {
  const [tab, setTab] = useState<TabKey>('lineart')
  const src = tab === 'original' ? original : result[tab]

  return (
    <div className="gallery">
      <div className="gallery__tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab${tab === t.key ? ' tab--active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="gallery__image">
        <img src={src} alt={tab} />
      </div>
      {tab !== 'original' && (
        <a className="download" href={src} download={`${tab}.png`}>
          Télécharger
        </a>
      )}
    </div>
  )
}
