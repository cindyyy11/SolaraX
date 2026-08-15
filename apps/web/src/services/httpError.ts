export class HttpError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body: unknown = null) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.body = body
  }
}

export function toHttpError(error: unknown): HttpError {
  if (error instanceof HttpError) {
    return error
  }

  if (error instanceof Error) {
    return new HttpError(error.message, 0, null)
  }

  return new HttpError(String(error), 0, null)
}
