import { describe, it, expect } from 'vitest'
import { HttpError, toHttpError } from './httpError'

describe('HttpError', () => {
  it('stores status and body', () => {
    const err = new HttpError('Nope', 404, { detail: 'missing' })
    expect(err.message).toBe('Nope')
    expect(err.status).toBe(404)
    expect(err.body).toEqual({ detail: 'missing' })
    expect(err.name).toBe('HttpError')
  })
})

describe('toHttpError', () => {
  it('returns the same instance when already HttpError', () => {
    const original = new HttpError('x', 500, null)
    expect(toHttpError(original)).toBe(original)
  })

  it('wraps a normal Error', () => {
    const wrapped = toHttpError(new Error('boom'))
    expect(wrapped).toBeInstanceOf(HttpError)
    expect(wrapped.message).toBe('boom')
    expect(wrapped.status).toBe(0)
  })

  it('wraps unknown values', () => {
    const wrapped = toHttpError('weird')
    expect(wrapped).toBeInstanceOf(HttpError)
    expect(wrapped.message).toBe('weird')
    expect(wrapped.status).toBe(0)
  })
})
