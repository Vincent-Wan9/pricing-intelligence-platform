# PricePilot frontend

React + TypeScript frontend for the Pricing Intelligence Platform.

## Run locally

Start the FastAPI backend on port 8000, then:

```bash
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`. For a separately hosted API,
copy `.env.example` to `.env` and set `VITE_API_URL` to its base URL. The API's
`cors_origins` setting accepts a comma-separated list of allowed frontend origins.

Authentication tokens are kept in `sessionStorage`, so they are cleared when the
browser tab is closed. All dashboard data is loaded from the backend; there are
no mocked records.
