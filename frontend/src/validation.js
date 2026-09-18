// Mirrors backend/app/validation.py. The server re-checks everything; these
// rules exist to give immediate, obvious feedback while typing.

export const LIMITS = {
  nameMaxLen: 50,
  messageMaxLen: 500,
  maxImageBytes: 5 * 1024 * 1024,
  allowedImageTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
}

const NAME_PUNCTUATION = new Set([' ', "'", '-', '.'])
const isLetter = (ch) => ch.toLowerCase() !== ch.toUpperCase() || /\p{L}/u.test(ch)

export function validateName(raw, label) {
  const value = (raw || '').trim().replace(/\s+/g, ' ')
  if (!value) return `${label} is required.`
  if (value.length > LIMITS.nameMaxLen)
    return `${label} must be ${LIMITS.nameMaxLen} characters or fewer.`
  if (![...value].some(isLetter)) return `${label} must contain at least one letter.`
  for (const ch of value) {
    if (!isLetter(ch) && !NAME_PUNCTUATION.has(ch))
      return `${label} may only contain letters, spaces, hyphens and apostrophes.`
  }
  return ''
}

export function validateMessage(raw) {
  const value = (raw || '').trim()
  if (!value) return 'Message is required.'
  if (value.length > LIMITS.messageMaxLen)
    return `Message must be ${LIMITS.messageMaxLen} characters or fewer.`
  return ''
}

export function validateImage(file) {
  if (!file) return ''
  if (!LIMITS.allowedImageTypes.includes(file.type))
    return 'Image must be a JPEG, PNG, GIF or WebP file.'
  if (file.size > LIMITS.maxImageBytes)
    return `Image must be smaller than ${Math.round(LIMITS.maxImageBytes / (1024 * 1024))} MB.`
  return ''
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function relativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return ''
  const seconds = Math.round((Date.now() - then.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
