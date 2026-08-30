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

The app lives in `apps/web`, not at the repo root, so `vercel.json` at the root does the redirection.
You should not need to set a Root Directory in the Vercel dashboard.

1. Sign in to [vercel.com](https://vercel.com) with the GitHub account that owns the repo.
2. **Add New → Project**, import `SolaraX`.
3. Leave every build setting on its default. `vercel.json` overrides them:
   - Build: `cd apps/web && npm ci && npm run build`
   - Output: `apps/web/dist`
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

## The vision service — deployed on Hugging Face Spaces

The M5 upload panel on Screen 2 posts an image to a FastAPI service. That service **is now deployed**:

- **URL:** `https://wenhuiiiiiii-solarax-vision.hf.space`  (`/health`, `POST /vision/predict`)
- **Space:** `wenhuiiiiiii/solarax-vision` — Gradio SDK, ZeroGPU (free) hardware
- **Source:** `deploy/vision-space/gradio/` (self-contained `app.py` — the classifier is inlined
  because a Gradio-SDK Space can't `git clone` this repo or import `pipeline.`). Keep it in sync
  with `pipeline/vision_api.py` + `pipeline/defect_classifier.py` by hand.

To switch the panel **on** for the deployed dashboard:

1. Vercel → SolaraX project → Settings → Environment Variables →
   `VITE_VISION_API_URL` = `https://wenhuiiiiiii-solarax-vision.hf.space` (Production, no trailing slash)
2. Redeploy (Vite inlines env vars at build time — a restart is not enough)

CORS: `app.py` allows `solara-x-inky.vercel.app` and `*.vercel.app` previews by default; override
with the `VISION_ALLOWED_ORIGINS` Space variable if the domain changes.

**Behaviour without the env var:** the panel stays hidden in production builds and the rest of
Screen 2 renders normally. `npm run dev` still defaults to `http://127.0.0.1:8000` for local M5 work.
Do **not** point it at a `http://127.0.0.1:8000`-style address in a deployed build — an HTTPS page
cannot call a plaintext localhost endpoint (mixed content), and it fails for every visitor.

**Cold start:** a free Space sleeps after 48h idle and takes ~40s to wake. Hit `/health` a few
minutes before any demo or judging window. ZeroGPU also has a daily free-usage quota.

The Docker-SDK variant in `deploy/vision-space/` (Dockerfile that builds from this repo) is kept as
a fallback — it needs an HF account with a payment method on file, which the Gradio route avoids.

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
