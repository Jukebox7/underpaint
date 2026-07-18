import { useCallback, useRef, useState } from 'react'

interface Props {
  onFile: (file: File) => void
  disabled?: boolean
  /** Barre discrète quand une image est déjà chargée (changer d'image). */
  compact?: boolean
  fileName?: string
}

export default function Dropzone({ onFile, disabled, compact, fileName }: Props) {
  const [hover, setHover] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0]
      if (file && file.type.startsWith('image/')) onFile(file)
    },
    [onFile],
  )

  return (
    <div
      className={`dropzone${compact ? ' dropzone--compact' : ''}${
        hover ? ' dropzone--hover' : ''
      }${disabled ? ' dropzone--disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setHover(true)
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault()
        setHover(false)
        if (!disabled) handleFiles(e.dataTransfer.files)
      }}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          handleFiles(e.target.files)
          e.target.value = '' // permet de re-choisir le même fichier
        }}
      />
      {compact ? (
        <p className="dropzone__hint">
          <strong>{fileName}</strong> — clique ou dépose ici pour changer d'image
        </p>
      ) : (
        <>
          <p className="dropzone__title">Dépose une image ici</p>
          <p className="dropzone__hint">ou clique pour en choisir une</p>
        </>
      )}
    </div>
  )
}
