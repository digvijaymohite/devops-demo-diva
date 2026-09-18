# Shoutout Board

A public board where students can post a shoutout to a classmate. No accounts and
no login — every post is signed with the writer's first and last name, and can
carry an optional photo.

## Architecture

```
 Browser ──HTTP:80──► nginx ──┬── /            → React bundle (static files)
                              └── /api/*       → uvicorn :8000 (FastAPI)
                                                     │
                                          ┌──────────┴──────────┐
                                          ▼                     ▼
                                 DynamoDB diva-shoutouts   S3 (private)
                                                       presigned GET URLs
```

Everything runs on a single EC2 instance in `ap-south-1`. The live board is at
<http://13.235.101.184/>. Concrete resource ids and teardown steps are in
[infra/RESOURCES.md](infra/RESOURCES.md).

| Piece | Resource |
| --- | --- |
| Compute | EC2 `t3.small`, Amazon Linux 2023 |
| Database | DynamoDB `diva-shoutouts`, on-demand billing |
| Images | S3 `diva-shoutout-images-851725336997` (private, presigned reads) |
| Identity | IAM role `diva-ec2-role` — SSM plus scoped table/bucket access |
| Admin access | SSM Session Manager only; port 22 is closed |

### Data model

One DynamoDB partition holds the whole board so it reads back as a single
time-ordered feed.

| Attribute | Type | Notes |
| --- | --- | --- |
| `board` | S (PK) | Always `main` |
| `posted_at` | S (SK) | `<ISO-8601 timestamp>#<uuid>` — sortable and collision-free |
| `id` | S | Public identifier |
| `first_name`, `last_name` | S | Validated, max 50 chars each |
| `message` | S | Max 500 chars |
| `image_key` | S | Optional S3 key under `images/` |

Reads use `Query` with `ScanIndexForward=false`, so newest posts come back
first and pagination is a cursor, not a scan.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness plus resolved table/bucket names |
| `GET` | `/api/config` | Validation limits, so the UI need not hardcode them |
| `GET` | `/api/shoutouts?limit=&cursor=` | Newest-first page of shoutouts |
| `POST` | `/api/shoutouts` | `multipart/form-data`: `first_name`, `last_name`, `message`, optional `image` |

Interactive docs are at `/api/docs`.

### Validation

`backend/app/validation.py` is authoritative; `frontend/src/validation.js`
mirrors it for instant feedback. The API is public, so the server never trusts
the client.

- **Names** — required, ≤ 50 chars, letters plus space / hyphen / apostrophe / period, at least one letter.
- **Message** — required, ≤ 500 chars, runaway blank lines collapsed.
- **Image** — optional, ≤ 5 MB, must be JPEG / PNG / GIF / WebP. The type is read
  from the file's magic bytes, not the client-supplied `Content-Type`.
- **Rate limit** — 5 posts per IP per 5 minutes, held in process memory. This is
  why the systemd unit runs a single uvicorn worker; extra workers would each
  keep their own counter and multiply the effective limit.

## Local development

Two terminals, from the repo root:

```bash
# Backend — needs AWS credentials that can reach the table and bucket
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export AWS_REGION=ap-south-1 \
       SHOUTOUTS_TABLE=diva-shoutouts \
       IMAGES_BUCKET=diva-shoutout-images-851725336997
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend — Vite proxies /api to port 8000
cd frontend
npm install
npm run dev
```

If your local AWS credentials come from `aws login` rather than a role or static
keys, botocore needs `pip install "botocore[crt]"` to read them. The instance
itself uses its IAM role, so it does not need that extra.

## Deployment

`deploy/bootstrap.sh` runs once from EC2 user-data: it installs nginx, Python
3.11 and Node 20, clones this repo, builds the frontend, and starts
`shoutout-api` under systemd behind nginx.

### Continuous deployment

Any commit to `main` ships automatically. `diva-shoutout-pipeline` watches the
repo through a CodeStar connection and runs three stages:

| Stage | What happens |
| --- | --- |
| Source | CodeStar connection pulls the commit from GitHub |
| Build | CodeBuild runs `buildspec.yml` — backend syntax check, `npm ci`, `npm run build` |
| Deploy | CodeDeploy pushes the bundle to the instance via `appspec.yml` |

CodeBuild produces the React bundle, so the instance needs neither Node nor a
network fetch at deploy time and `deploy/bootstrap.sh` only has to prepare the
host. The deploy hooks live in `deploy/hooks/`:

| Hook | Role |
| --- | --- |
| `stop.sh` | Stops the service; tolerates it being absent |
| `before_install.sh` | Ensures the service user and directories exist |
| `after_install.sh` | Syncs the venv, publishes the bundle, installs unit and nginx config |
| `start.sh` | Starts the API and reloads nginx |
| `validate.sh` | Polls `/api/health` and `/`; a failure fails the deployment |

`validate.sh` is what makes a rollback meaningful — the deployment group has
automatic rollback on failure, so a revision that cannot serve traffic is
replaced by the last good one instead of staying live.

The release lives at `/opt/shoutout/release`; the virtualenv sits outside it at
`/opt/shoutout/venv` so it survives deployments.

Open a shell on the box with `aws ssm start-session --target <instance-id>`.

## Operational notes

- The board is served over **HTTP**, not HTTPS. Browsers will mark it "Not
  secure". Adding TLS needs a domain name pointed at the instance plus certbot.
- Anyone can post, and nothing is moderated. The rate limit slows casual
  flooding but is not abuse prevention — there is no CAPTCHA and no review queue.
- Image URLs are presigned and expire after an hour; the page fetches fresh ones
  on every load, so the bucket itself stays private.
- State lives entirely in DynamoDB and S3. The instance is disposable — losing it
  costs no data.
