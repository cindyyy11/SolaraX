# DEPLOY.md — getting the dashboard onto a public URL

> **Why this file exists.** `hinfo/SUBMISSION-CHECKLIST.md` lists a hosted demo as an optional-but-
> decisive deliverable, and red-team item 8 is *"Is the dashboard URL public and loading without a
> login?"*. Until early Sept there is no answer to that question, and a judging window is not the
> moment to discover a deployment problem.

Everything here is already configured in the repo. What is left needs a human with the accounts.

---

## Before anything else — make the repo public

`https://github.com/cindyyy11/SolaraX` currently returns **404** to anyone who is not a collaborator.

Per `hinfo/HACKATHON.md`, the artifact **must stay publicly accessible during judging**. A private
repo during the judging window counts as **non-submission** — not as a lower score.

> GitHub → the repo → **Settings** → scroll to **Danger Zone** → **Change repository visibility** →
> **Make public**.

Takes about thirty seconds. Nothing else in this file matters until it is done.

---

## Deploying the frontend to Vercel

The app lives in `apps/web`. Set **Root Directory** to `apps/web` in the Vercel dashboard;
the root `vercel.json` commands are evaluated from that directory.

1. Sign in to [vercel.com](https://vercel.com) with the GitHub account that owns the repo.
2. **Add New → Project**, import `SolaraX`.
3. Leave every build setting on its default. `vercel.json` overrides them:
   - Install: `npm ci`
   - Build: `npm run build`
   - Output: `dist`
   - Framework preset: none (Vite is driven through the build command)
4. **Environment variables — leave them empty.** See the note on the vision service below.
5. Deploy. First build takes about a minute.

### What `vercel.json` handles that a default deploy would get wrong

**SPA rewrites.** The router uses `createWebHistory`, so `/site/S-1276` is a client-side route with
no file behind it. Without a rewrite, a judge who opens a site link directly — or simply refreshes
the page they are looking at — gets a **404 from the CDN**. The catch-all rewrite sends unmatched
paths to `index.html` and lets the router resolve them.

It is a plain `/(.*)` catch-all deliberately, with no exclusion list. Vercel checks the **filesystem
before applying rewrites**, so real files — the hashed asset bundles, `dispatch.json`,
`dispatch.mock.json`, `favicon.ico` — are served as themselves and never reach the rule. Writing a
negative-lookahead exclusion instead would add a regex that cannot be tested until deploy time in
order to prevent something that cannot happen.

That ordering matters for one specific failure: if `dispatch.json` ever did fall through to the
rewrite, the data-access layer would fetch `index.html`, try to parse HTML as JSON, and the dashboard
would render empty with a console error rather than a useful failure. Worth knowing as a symptom.

**Cache headers.** Hashed asset bundles are immutable and cached for a year. `dispatch.json` is
explicitly `must-revalidate`, so regenerating the artifact and pushing shows up immediately instead
of being served stale from the edge for the length of the judging window.

---

## The vision service — leave `VITE_VISION_API_URL` unset

The M5 upload panel on Screen 2 posts an image to a FastAPI service. That service is **not deployed**,
and until it is, the correct configuration is no configuration:

- Unset, the panel is **hidden** in production builds and the rest of Screen 2 renders normally.
- Set to a `http://127.0.0.1:8000`-style address, the panel renders on the public site, accepts a
  file, and then fails for every visitor — a deployed page is served over HTTPS, and browsers block
  plaintext requests to localhost from an HTTPS origin as mixed content.

Local development is unaffected: `npm run dev` still defaults to `http://127.0.0.1:8000`, so B can
work on M5 exactly as before.

If the service is later deployed (Hugging Face Spaces is the choice in `CLAUDE.md`), set
`VITE_VISION_API_URL` to its **HTTPS** URL in Vercel and add the Vercel domain to the CORS allow-list
in `pipeline/vision_api.py`, which currently permits `http://localhost:5173` only.

---

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

1. Installs the pipeline dependencies and runs the **full test suite**.
2. Runs `validate_dispatch.py` against the committed artifact — so a `dispatch.json` that has drifted
   out of schema conformance fails the build rather than a demo.
3. Type-checks and builds the frontend.

It does **not** regenerate `dispatch.json` on a schedule. That was considered and rejected: a nightly
job depends on NASA POWER and the PVDAQ S3 bucket both being reachable, and a failure during the
judging window would replace a working committed artifact with a broken one. `ARCHITECTURE-PLAN.md`
§3.5 already flags the scheduled job as a single point of failure. The artifact is committed, the
frontend falls back to it, and regeneration is a deliberate local step.

---

## Checking it actually works

Once the URL is live, walk these in a **private/incognito window** — that is what catches an auth
wall, and it is exactly how a judge will arrive:

- [ ] Root URL loads Screen 1 with no login prompt
- [ ] Fleet map renders; the five stacked Las Vegas markers cluster rather than overlapping
- [ ] Click through to a site detail page
- [ ] **Refresh that page.** It must still load — this is the rewrite rule doing its job
- [ ] Paste the site-detail URL into a fresh tab. Same test, different failure mode
- [ ] Work-order screen opens
- [ ] Browser console is clean — no mixed-content warnings, no failed fetches
- [ ] `<your-url>/dispatch.json` returns JSON, not HTML

---

*Owner: D (Chang Zhe) for the deployment; repo visibility is Cindy's — she owns the GitHub account.*
