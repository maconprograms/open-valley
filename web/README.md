# Open Valley web dashboard

This Next.js application currently serves the Warren evidence-first baseline at
`/`.

## Development

```bash
npm install
npm run dev -- -p 3999
```

The default rewrite sends `/api/baseline/*` to the standalone baseline API on
port 8998. Start that API from the repository root with:

```bash
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998
```

Set `INTERNAL_BASELINE_API_URL` for the server-side proxy in another environment.
`NEXT_PUBLIC_BASELINE_API_URL` is optional and should only point to a
CORS-configured direct API.

## Quality checks

```bash
npm test
npx eslint src/components/baseline src/app/layout.tsx
npm run build
```

The focused tests cover the MapLibre feature-property normalization used by the
click panel and hover tooltip. The repo-wide lint command includes older,
separately maintained surfaces and is not yet green.
