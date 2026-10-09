import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { AlertIcon, SendIcon } from '../components/icons'
import Markdown from '../components/Markdown'
import { Button, Card } from '../components/ui'

type UiMessage = {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

const SUGGESTIONS = [
  'What is PCOS?',
  'How can I lose weight with PCOS?',
  'What tests are done for PCOS?',
  'Diet tips for insulin resistance',
]

function loadHistory(): UiMessage[] {
  try {
    const raw = sessionStorage.getItem('pcos.chat')
    return raw ? (JSON.parse(raw) as UiMessage[]) : []
  } catch {
    return []
  }
}

export default function Chat() {
  const [messages, setMessages] = useState<UiMessage[]>(loadHistory)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem('pcos.chatSession')
    } catch {
      return null
    }
  })
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    try {
      sessionStorage.setItem('pcos.chat', JSON.stringify(messages))
    } catch {
      // storage unavailable — keep in memory only
    }
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || sending) return
    setError(null)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setSending(true)
    try {
      const res = await api.chat(message, sessionId)
      setSessionId(res.session_id)
      try {
        sessionStorage.setItem('pcos.chatSession', res.session_id)
      } catch {
        // ignore
      }
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.response, sources: res.sources },
      ])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reach the assistant.')
    } finally {
      setSending(false)
    }
  }

  const clear = () => {
    setMessages([])
    setSessionId(null)
    setError(null)
    try {
      sessionStorage.removeItem('pcos.chat')
      sessionStorage.removeItem('pcos.chatSession')
    } catch {
      // ignore
    }
  }

  return (
    <div className="page chat-page">
      <Card className="chat-card">
        <header className="chat-header">
          <div>
            <h2 className="card-title">Health assistant</h2>
            <p className="card-subtitle">Answers grounded in your PCOS knowledge base</p>
          </div>
          {messages.length > 0 && (
            <Button variant="ghost" onClick={clear}>
              Clear chat
            </Button>
          )}
        </header>

        <div className="chat-log">
          {messages.length === 0 && (
            <div className="chat-empty">
              <p className="chat-empty-title">Ask anything about PCOS</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => void send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`bubble-row ${m.role}`}>
              <div className={`bubble ${m.role}`}>
                <div className="bubble-text">
                  <Markdown content={m.content} />
                </div>
                {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                  <p className="bubble-sources">Sources: {m.sources.join(', ')}</p>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="bubble-row assistant">
              <div className="bubble assistant typing">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}

          {error && (
            <div className="alert alert-error" role="alert">
              <AlertIcon size={17} />
              <span>{error}</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form
          className="chat-input-row"
          onSubmit={(e) => {
            e.preventDefault()
            void send(input)
          }}
        >
          <input
            className="input chat-input"
            type="text"
            placeholder="Type your question…"
            value={input}
            maxLength={2000}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="submit" disabled={sending || !input.trim()}>
            <SendIcon size={18} />
            <span className="send-label">Send</span>
          </Button>
        </form>
      </Card>

      <p className="disclaimer">
        The assistant offers general education, not medical advice. For urgent symptoms contact a
        clinician.
      </p>
    </div>
  )
}
