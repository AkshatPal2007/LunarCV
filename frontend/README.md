# LunarCV Frontend

React/Vite visualization console for the LunarCV image-registration backend.
It presents the pipeline, geographic context, correspondence points, and
available registration products through a browser interface.

## Requirements

- Node.js 18 or newer
- npm
- A running LunarCV API when using live backend data

## Install and Run

From the repository root:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Vite normally serves the frontend at `http://localhost:5173`. The API base URL
is configured with `VITE_API_URL`; the local default is
`http://localhost:8000/api/v1`.

## Available Scripts

```bash
npm --prefix frontend run dev
npm --prefix frontend run build
npm --prefix frontend run preview
npm --prefix frontend run lint
```

## Stack

The frontend uses React 19, Vite, Framer Motion, Lucide React, Tailwind CSS
(via the Vite plugin), and Oxlint. The package is private and is not published
as a standalone npm package.
