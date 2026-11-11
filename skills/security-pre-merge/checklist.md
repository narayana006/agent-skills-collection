# Pre-merge security checklist

Apply each item to the changed code only.

## Secrets and configuration
- No credentials, tokens, private keys or connection strings in code, tests, fixtures or config.
- New configuration is read from the environment or a secret store, with no insecure fallback.
- Debug modes, verbose errors and permissive CORS are not enabled for production.

## Input handling
- Every new input from outside the trust boundary is validated for type, length and range.
- SQL is parameterised. No query is built by string concatenation or formatting.
- Nothing from a request reaches a shell, `eval`, a template compiled at run time, or a
  deserialiser that can construct arbitrary objects.
- File paths built from input are resolved and checked to stay inside the intended directory.
- URLs fetched on behalf of a user are restricted, so internal addresses cannot be reached.

## Authentication and authorisation
- Each new endpoint or action checks that the caller is authenticated.
- It also checks that the caller may act on this particular object, not just any object.
- Session, token and password handling use the framework's facilities, not hand-rolled crypto.

## Output and data exposure
- User-controlled content is escaped for the context it is rendered in (HTML, attribute, URL).
- Responses and logs do not include secrets, tokens, full card or ID numbers, or stack traces.
- New fields added to an API response are meant to be visible to every caller of that API.

## Dependencies and transport
- New dependencies are needed, maintained and pinned; the lockfile is updated.
- TLS verification is not disabled. Outbound calls have timeouts.

## Change hygiene
- Removed checks (validation, auth, rate limits) were removed on purpose and replaced if needed.
- Migrations and scripts do not widen permissions or expose data as a side effect.
