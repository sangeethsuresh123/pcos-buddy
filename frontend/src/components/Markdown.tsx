import { Fragment, type ReactNode } from 'react'

const INLINE_RE = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`\n]+`|\[[^\]]+\]\((?:https?:|mailto:)[^\s)]+\))/g

const HEADING_RE = /^(#{1,6})\s+(.*)$/
const UL_RE = /^\s*[-*+]\s+(.*)$/
const OL_RE = /^\s*\d+[.)]\s+(.*)$/

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(INLINE_RE)
  return parts.map((part, i) => {
    if (!part) return null
    const key = `${keyPrefix}-${i}`

    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('__') && part.endsWith('__') && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={key}>{part.slice(1, -1)}</code>
    }
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      return (
        <a key={key} href={link[2]} target="_blank" rel="noopener noreferrer">
          {link[1]}
        </a>
      )
    }
    if (
      (part.startsWith('*') && part.endsWith('*')) ||
      (part.startsWith('_') && part.endsWith('_'))
    ) {
      if (part.length > 2) return <em key={key}>{part.slice(1, -1)}</em>
    }
    return <Fragment key={key}>{part}</Fragment>
  })
}

function isBlockStart(line: string): boolean {
  return HEADING_RE.test(line) || UL_RE.test(line) || OL_RE.test(line)
}

export default function Markdown({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    if (!line.trim()) {
      i++
      continue
    }

    const heading = line.match(HEADING_RE)
    if (heading) {
      const level = heading[1].length
      const text = heading[2]
      blocks.push(
        level <= 2 ? (
          <h4 key={key++}>{renderInline(text, `h${key}`)}</h4>
        ) : (
          <h5 key={key++}>{renderInline(text, `h${key}`)}</h5>
        ),
      )
      i++
      continue
    }

    if (UL_RE.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length) {
        const match = lines[i].match(UL_RE)
        if (!match) break
        items.push(<li key={items.length}>{renderInline(match[1], `ul${key}-${items.length}`)}</li>)
        i++
      }
      blocks.push(<ul key={key++}>{items}</ul>)
      continue
    }

    if (OL_RE.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length) {
        const match = lines[i].match(OL_RE)
        if (!match) break
        items.push(<li key={items.length}>{renderInline(match[1], `ol${key}-${items.length}`)}</li>)
        i++
      }
      blocks.push(<ol key={key++}>{items}</ol>)
      continue
    }

    const paragraph: string[] = []
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) {
      paragraph.push(lines[i])
      i++
    }
    blocks.push(
      <p key={key++}>
        {paragraph.map((text, idx) => (
          <Fragment key={idx}>
            {renderInline(text, `p${key}-${idx}`)}
            {idx < paragraph.length - 1 && <br />}
          </Fragment>
        ))}
      </p>,
    )
  }

  return <>{blocks}</>
}
