import { useCallback, useEffect, useState } from 'react'
import ShoutoutForm from './components/ShoutoutForm.jsx'
import ShoutoutCard from './components/ShoutoutCard.jsx'
import { fetchShoutouts, postShoutout } from './api.js'

const PAGE_SIZE = 20

export default function App() {
  const [shoutouts, setShoutouts] = useState([])
  const [cursor, setCursor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [loadError, setLoadError] = useState('')

  const load = useCallback(async (nextCursor) => {
    const isFirstPage = !nextCursor
    isFirstPage ? setLoading(true) : setLoadingMore(true)
    try {
      const data = await fetchShoutouts({ limit: PAGE_SIZE, cursor: nextCursor })
      setShoutouts((prev) => (isFirstPage ? data.shoutouts : [...prev, ...data.shoutouts]))
      setCursor(data.next_cursor)
      setLoadError('')
    } catch (error) {
      setLoadError(error.message)
    } finally {
      isFirstPage ? setLoading(false) : setLoadingMore(false)
    }
  }, [])

  useEffect(() => { load(null) }, [load])

  async function handlePost(payload) {
    const created = await postShoutout(payload)
    // Drop it straight on top rather than refetching the whole first page.
    setShoutouts((prev) => [created, ...prev])
    return created
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead__inner">
          <h1>Shoutout Board For Div A</h1>
          <p>Celebrate a classmate. Anyone can post — just sign it with your name.</p>
        </div>
      </header>

      <main className="layout">
        <ShoutoutForm onPosted={handlePost} />

        <section className="feed" aria-live="polite">
          <h2 className="feed__title">
            Recent shoutouts {shoutouts.length > 0 && <span className="pill">{shoutouts.length}</span>}
          </h2>

          {loading && <p className="muted">Loading the board…</p>}

          {!loading && loadError && (
            <div className="card empty">
              <p className="error">{loadError}</p>
              <button className="btn btn--ghost" onClick={() => load(null)}>Try again</button>
            </div>
          )}

          {!loading && !loadError && shoutouts.length === 0 && (
            <div className="card empty">
              <p className="empty__title">No shoutouts yet</p>
              <p className="muted">Be the first to say something kind.</p>
            </div>
          )}

          <div className="grid">
            {shoutouts.map((shoutout) => (
              <ShoutoutCard key={shoutout.id} shoutout={shoutout} />
            ))}
          </div>

          {cursor && !loadError && (
            <button className="btn btn--ghost btn--block" disabled={loadingMore}
                    onClick={() => load(cursor)}>
              {loadingMore ? 'Loading…' : 'Load older shoutouts'}
            </button>
          )}
        </section>
      </main>

      <footer className="footer">
        <p>Public board · be kind · posts are visible to everyone</p>
      </footer>
    </div>
  )
}
