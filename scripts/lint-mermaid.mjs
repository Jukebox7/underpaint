#!/usr/bin/env node
// Lint heuristique des blocs ```mermaid``` : attrape les erreurs de syntaxe
// les plus courantes qui cassent le rendu dans le viewer FJ Docs.
// Usage: node scripts/lint-mermaid.mjs [glob...]   (défaut: docs/**/*.md)
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

function walk(dir) {
  const out = []
  for (const e of readdirSync(dir)) {
    const p = join(dir, e)
    const st = statSync(p)
    if (st.isDirectory()) out.push(...walk(p))
    else if (p.endsWith('.md')) out.push(p)
  }
  return out
}

const args = process.argv.slice(2)
const files = (args.length ? args : walk('docs'))

const RESERVED = new Set(['end', 'class', 'click', 'style', 'subgraph'])
let problems = 0

function lintBlock(file, startLine, lines) {
  const issues = []
  const text = lines.join('\n')
  const header = (lines[0] || '').trim().split(/\s+/)[0]
  const isFlowish = /^(flowchart|graph)/.test(text.trim())

  lines.forEach((raw, i) => {
    const ln = startLine + i + 1
    const line = raw.replace(/%%.*$/, '') // strip comments

    // 1) Labels avec parenthèses/crochets non quotés: [...], {...}, (...)
    //    On extrait le contenu des labels et on vérifie les caractères pièges.
    const labelRe = /(\[\[?|\{\{?|\(\(?|\(\[|>)([^\]\}\)\|]*?)(\]\]?|\}\}?|\)\)?|\]\)|)/g
    let m
    while ((m = labelRe.exec(line)) !== null) {
      const inner = m[2]
      if (!inner) continue
      const quoted = /^\s*"/.test(inner) || /"\s*$/.test(inner)
      if (!quoted && /[()]/.test(inner)) {
        issues.push(`L${ln}: parenthèse non quotée dans un label → "${inner.trim()}" (entourer de "...")`)
      }
    }

    // 2) node id réservé (ex: end --> ...)
    if (isFlowish) {
      const idm = line.match(/^\s*([A-Za-z_][\w-]*)\s*(\[|\(|\{|-->|---|==>)/)
      if (idm && RESERVED.has(idm[1].toLowerCase())) {
        issues.push(`L${ln}: identifiant réservé "${idm[1]}" utilisé comme node id`)
      }
    }

    // 3) guillemets déséquilibrés sur la ligne
    const q = (line.match(/"/g) || []).length
    if (q % 2 !== 0) issues.push(`L${ln}: nombre impair de guillemets`)
  })

  // 4) crochets globaux déséquilibrés
  const open = (text.match(/\[/g) || []).length
  const close = (text.match(/\]/g) || []).length
  if (open !== close) issues.push(`bloc: crochets [ ] déséquilibrés (${open} vs ${close})`)

  if (issues.length) {
    problems += issues.length
    console.log(`\n✗ ${file}  (bloc mermaid L${startLine + 1}, type: ${header})`)
    issues.forEach(s => console.log('   ' + s))
  }
}

for (const file of files) {
  const src = readFileSync(file, 'utf8').split('\n')
  let inBlock = false, blockStart = 0, buf = []
  src.forEach((line, i) => {
    if (!inBlock && /^```mermaid\s*$/.test(line.trim())) { inBlock = true; blockStart = i; buf = []; return }
    if (inBlock && /^```\s*$/.test(line.trim())) { lintBlock(file, blockStart, buf); inBlock = false; return }
    if (inBlock) buf.push(line)
  })
}

if (problems === 0) console.log('✓ Aucun problème Mermaid détecté.')
else { console.log(`\n${problems} problème(s) potentiel(s).`); process.exit(1) }
