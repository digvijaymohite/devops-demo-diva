import { relativeTime } from '../validation.js'

// Deterministic accent per person so the board looks varied but stable.
const ACCENTS = ['a', 'b', 'c', 'd', 'e', 'f']

function accentFor(name) {
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.codePointAt(0)) % 997
  return ACCENTS[hash % ACCENTS.length]
}

export default function ShoutoutCard({ shoutout }) {
  const { first_name: first, last_name: last, message, created_at: createdAt, image_url: imageUrl } = shoutout
  const fullName = `${first} ${last}`.trim()
  const initials = `${first?.[0] || ''}${last?.[0] || ''}`.toUpperCase()

  return (
    <article className="card shoutout">
      <header className="shoutout__head">
        <span className={`avatar avatar--${accentFor(fullName)}`} aria-hidden="true">{initials}</span>
        <div>
          <p className="shoutout__name">{fullName}</p>
          <time className="shoutout__time" dateTime={createdAt}>{relativeTime(createdAt)}</time>
        </div>
      </header>
      <p className="shoutout__message">{message}</p>
      {imageUrl && (
        <a className="shoutout__media" href={imageUrl} target="_blank" rel="noreferrer noopener">
          <img src={imageUrl} alt={`Photo shared by ${fullName}`} loading="lazy" />
        </a>
      )}
    </article>
  )
}
