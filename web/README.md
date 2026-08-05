# Open Valley web

The Next.js dashboard is the public Open Valley interface. It calls only
same-origin `/api/baseline/*` paths; the server-side deployment proxy reaches
the internal release-reader API.

## Development

```bash
npm install
npm run dev -- -p 3999
```

Start the redacted release-reader API from the repository root when previewing
the dashboard. Do not configure `NEXT_PUBLIC_BASELINE_API_URL` or direct browser
access to an API or database.

## Checks

```bash
npm test
npm run lint
npm run build
```

The map's keyboard parcel list is a required equivalent for pointer map
interaction. Keep loading, unavailable, incomplete, and malformed-data states
plainly understandable without exposing private data.
