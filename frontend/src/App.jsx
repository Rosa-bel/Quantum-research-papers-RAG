import { useEffect, useRef, useState } from 'react';

const suggestedPrompts = [
  'Explain Variational Quantum Eigensolver (VQE)',
  'Summarize surface code threshold requirements',
  'What error mitigation techniques are evaluated?',
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [backend, setBackend] = useState('Checking backend…');
  const [online, setOnline] = useState(false);
  const textareaRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    fetch('/health')
      .then((response) => {
        if (!response.ok) throw new Error('Backend unavailable');
        setOnline(true);
        setBackend('Backend connected');
      })
      .catch(() => {
        setOnline(false);
        setBackend('Backend offline');
      });
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function sendMessage(value = prompt) {
    const question = value.trim();
    if (!question || loading) return;

    setMessages((current) => [...current, { role: 'user', text: question }]);
    setPrompt('');
    setLoading(true);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: question }),
      });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      setMessages((current) => [...current, { role: 'assistant', text: data.response }]);
      setOnline(true);
      setBackend('Backend connected');
    } catch (error) {
      setOnline(false);
      setBackend('Backend offline');
      setMessages((current) => [
        ...current,
        { role: 'error', text: `Could not reach the backend. ${error.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([]);
    setPrompt('');
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Quantum Papers RAG</h1>
          <p>Literature search &amp; synthesis</p>
        </div>
        <div className="topbar-actions">
          <span className={`status ${online ? 'online' : 'offline'}`}>
            <i />{backend}
          </span>
          <button className="clear-button" onClick={clearChat} disabled={!messages.length}>
            Clear chat
          </button>
        </div>
      </header>

      <main className="conversation">
        {!messages.length ? (
          <section className="welcome">
            <div className="mark">Q</div>
            <h2>Quantum Research Assistant</h2>
            <p>Ask questions about indexed quantum computing papers and their sources.</p>
            <div className="suggestions">
              {suggestedPrompts.map((item) => (
                <button key={item} onClick={() => sendMessage(item)} disabled={loading}>
                  {item}
                </button>
              ))}
            </div>
          </section>
        ) : (
          <section className="messages" aria-live="polite">
            {messages.map((message, index) => (
              <article className={`message ${message.role}`} key={`${index}-${message.role}`}>
                <span className="message-label">
                  {message.role === 'user' ? 'You' : message.role === 'error' ? 'Connection error' : 'Assistant'}
                </span>
                <p>{message.text}</p>
              </article>
            ))}
            {loading && <div className="loading">Searching papers and generating an answer…</div>}
            <div ref={endRef} />
          </section>
        )}
      </main>

      <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(event) => {
            setPrompt(event.target.value);
            event.target.style.height = 'auto';
            event.target.style.height = `${Math.min(event.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Ask a question about quantum computing papers…"
          rows={2}
          disabled={loading}
        />
        <div className="composer-footer">
          <span>Enter to send · Shift + Enter for a new line</span>
          <button type="submit" disabled={!prompt.trim() || loading}>Send</button>
        </div>
      </form>
    </div>
  );
}
