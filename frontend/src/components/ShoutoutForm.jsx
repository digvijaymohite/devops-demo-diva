import { useEffect, useMemo, useRef, useState } from 'react'
import {
  LIMITS, formatBytes, validateImage, validateMessage, validateName,
} from '../validation.js'

const EMPTY = { firstName: '', lastName: '', message: '' }

export default function ShoutoutForm({ onPosted }) {
  const [values, setValues] = useState(EMPTY)
  const [touched, setTouched] = useState({})
  const [image, setImage] = useState(null)
  const [imageError, setImageError] = useState('')
  const [preview, setPreview] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const fileInput = useRef(null)

  const errors = useMemo(() => ({
    firstName: validateName(values.firstName, 'First name'),
    lastName: validateName(values.lastName, 'Last name'),
    message: validateMessage(values.message),
  }), [values])

  const isValid = !errors.firstName && !errors.lastName && !errors.message && !imageError

  useEffect(() => {
    if (!image) { setPreview(''); return }
    const url = URL.createObjectURL(image)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [image])

  const update = (field) => (event) => {
    setValues((prev) => ({ ...prev, [field]: event.target.value }))
    setFormError('')
  }
  const blur = (field) => () => setTouched((prev) => ({ ...prev, [field]: true }))
  const show = (field) => (touched[field] ? errors[field] : '')

  function pickImage(event) {
    const file = event.target.files?.[0] || null
    const problem = validateImage(file)
    setImageError(problem)
    setImage(problem ? null : file)
    if (problem && fileInput.current) fileInput.current.value = ''
    setFormError('')
  }

  function clearImage() {
    setImage(null)
    setImageError('')
    if (fileInput.current) fileInput.current.value = ''
  }

  function reset() {
    setValues(EMPTY)
    setTouched({})
    clearImage()
  }

  async function submit(event) {
    event.preventDefault()
    setTouched({ firstName: true, lastName: true, message: true })
    if (!isValid || submitting) return
    setSubmitting(true)
    setFormError('')
    try {
      const created = await onPosted({
        firstName: values.firstName.trim().replace(/\s+/g, ' '),
        lastName: values.lastName.trim().replace(/\s+/g, ' '),
        message: values.message.trim(),
        image,
      })
      if (created) reset()
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const remaining = LIMITS.messageMaxLen - values.message.length

  return (
    <form className="card form" onSubmit={submit} noValidate>
      <h2 className="form__title">Post a shoutout</h2>
      <p className="form__hint">
        Everyone can see this board. Add your name so people know who it is from.
      </p>

      <div className="field-row">
        <Field
          id="firstName" label="First name" value={values.firstName}
          onChange={update('firstName')} onBlur={blur('firstName')}
          error={show('firstName')} maxLength={LIMITS.nameMaxLen}
          autoComplete="given-name" placeholder="Asha"
        />
        <Field
          id="lastName" label="Last name" value={values.lastName}
          onChange={update('lastName')} onBlur={blur('lastName')}
          error={show('lastName')} maxLength={LIMITS.nameMaxLen}
          autoComplete="family-name" placeholder="Kulkarni"
        />
      </div>

      <div className="field">
        <div className="field__head">
          <label className="field__label" htmlFor="message">Message</label>
          <span className={`counter ${remaining < 0 ? 'counter--over' : ''}`}>
            {remaining} left
          </span>
        </div>
        <textarea
          id="message" rows={4} value={values.message}
          onChange={update('message')} onBlur={blur('message')}
          maxLength={LIMITS.messageMaxLen}
          aria-invalid={Boolean(show('message'))}
          aria-describedby={show('message') ? 'message-error' : undefined}
          className={show('message') ? 'input input--error' : 'input'}
          placeholder="Great job on the science fair project!"
        />
        {show('message') && <p className="error" id="message-error">{show('message')}</p>}
      </div>

      <div className="field">
        <label className="field__label" htmlFor="image">Photo <span className="optional">optional</span></label>
        <input
          ref={fileInput} id="image" type="file" className="file"
          accept={LIMITS.allowedImageTypes.join(',')} onChange={pickImage}
        />
        <p className="field__note">
          JPEG, PNG, GIF or WebP, up to {formatBytes(LIMITS.maxImageBytes)}.
        </p>
        {imageError && <p className="error">{imageError}</p>}
        {preview && (
          <div className="preview">
            <img src={preview} alt="Selected upload preview" />
            <button type="button" className="btn btn--ghost" onClick={clearImage}>
              Remove photo
            </button>
          </div>
        )}
      </div>

      {formError && <p className="error error--banner" role="alert">{formError}</p>}

      <button type="submit" className="btn btn--primary" disabled={!isValid || submitting}>
        {submitting ? 'Posting…' : 'Post shoutout'}
      </button>
    </form>
  )
}

function Field({ id, label, error, ...props }) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>{label}</label>
      <input
        id={id} type="text" className={error ? 'input input--error' : 'input'}
        aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error && <p className="error" id={`${id}-error`}>{error}</p>}
    </div>
  )
}
