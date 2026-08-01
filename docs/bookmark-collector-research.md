# Bookmark Collector — Research & Design

> Status: **Research phase — exploring Karakeep next**
> Date: 2026-08-01
> Context: Collecting personal bookmarks/saves from multiple platforms into Obsidian LLM Wiki, feeding AI agents for analysis.

---

## Problem

Collect bookmarks, saved posts, likes, and stocks from multiple platforms automatically, aggregate them in one place, and feed them to AI agents for analysis — ultimately distilling them into permanent wiki pages in the Obsidian vault.

## Sources — API Availability

| Source | Type | API / Method | Auth Needed | Viability |
|--------|------|-------------|-------------|-----------|
| **X Bookmarks** | Social saves | `GET /2/users/:id/bookmarks` (X API v2) | OAuth 2.0, `bookmark.read` scope | ✅ Good |
| **Qiita Stocks** | Dev saves | `GET /api/v2/users/:user_id/stocks` | Bearer token (`read_qiita`) | ✅ Solid |
| **Zenn Likes** | Dev likes | `GET /api/articles?username=<user>&order=liked` | None (public) | ⚠️ Partial — likes, not bookmarks |
| **Chrome Bookmarks** | Browser | Local JSON file at `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks` | None | ✅ Trivial |
| **GitHub Stars** | Code saves | `GET /user/starred` | GitHub PAT | ✅ Good |
| **HN Upvotes** | Social saves | Firebase API `v0/user/<user>/submitted.json` + auth cookie | Auth cookie | ✅ Doable |
| **Reddit Saves** | Social saves | Reddit OAuth `GET /api/v1/me/saved` | OAuth 2.0 | ✅ Good |
| **Threads Saved** | Social saves | No public API | — | ❌ Blocked |
| **Instagram Saved** | Social saves | No public API | — | ❌ Blocked |
| **Any URL (mobile)** | Manual save | Share sheet → Telegram / Karakeep / Raindrop | Varies | ⚠️ Workaround |

### Removed

- **GitHub Trending** — Not personal saves; algorithmic noise. Removed per user request.

## Repos Researched

### Self-Hosted Bookmark Managers (Storage Layer)

| Repo | Stars | Description |
|------|-------|-------------|
| [karakeep-app/karakeep](https://github.com/karakeep-app/karakeep) | ★27,961 | AI-powered bookmark-everything app. Mobile app, REST API, auto-tagging, auto-crawl. Runs on Docker (PostgreSQL + Meilisearch) |
| [sidoshi/karakeep-sync](https://github.com/sidoshi/karakeep-sync) | ★125 | Syncs HN upvotes, Reddit saves, GitHub stars, Pinboard → Karakeep. X bookmarks planned |
| [linkwarden/linkwarden](https://github.com/linkwarden/linkwarden) | ★19,242 | Self-hosted collaborative bookmark manager |
| [wallabag/wallabag](https://github.com/wallabag/wallabag) | ★12,869 | Read-it-later service, REST API |
| [go-shiori/shiori](https://github.com/go-shiori/shiori) | ★11,562 | Minimal bookmark manager in Go |
| [sissbruecker/linkding](https://github.com/sissbruecker/linkding) | ★10,981 | Minimal self-hosted bookmark manager |

### Web Archiving

| Repo | Stars | Description |
|------|-------|-------------|
| [ArchiveBox/ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) | ★28,064 | Self-hosted web archiving. Imports bookmarks/browser history |
| [omnivore-app/omnivore](https://github.com/omnivore-app/omnivore) | ★16,203 | Open source read-it-later solution |

### RSS & Monitoring

| Repo | Stars | Description |
|------|-------|-------------|
| [DIYgod/RSSHub](https://github.com/DIYgod/RSSHub) | ★45,497 | Universal RSS generator — turns any site into RSS |
| [dgtlmoon/changedetection.io](https://github.com/dgtlmoon/changedetection.io) | ★32,571 | Website change detection & monitoring |
| [huginn/huginn](https://github.com/huginn/huginn) | ★49,733 | Agent automation — scrape, monitor, act |
| [RSS-Bridge/rss-bridge](https://github.com/RSS-Bridge/rss-bridge) | ★9,130 | RSS for sites without RSS |
| [miniflux/v2](https://github.com/miniflux/v2) | ★9,537 | Minimalist RSS reader with REST API |
| [FreshRSS/FreshRSS](https://github.com/FreshRSS/FreshRSS) | ★15,658 | Full-featured RSS reader with API |

### Content Extraction (URL → Clean Text)

| Repo | Stars | Description |
|------|-------|-------------|
| [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | ★158,869 | URL → LLM-ready markdown. Cloud or self-hosted |
| [gildas-lormeau/SingleFile](https://github.com/gildas-lormeau/SingleFile) | ★22,055 | Save faithful copy of any page as single HTML |
| [codelucas/newspaper](https://github.com/codelucas/newspaper) | ★15,133 | Python article extraction with NLP |
| [adbar/trafilatura](https://github.com/adbar/trafilatura) | ★6,381 | Python CLI & lib for web text extraction |

### X Bookmark Exporters (Small Projects)

| Repo | Description |
|------|-------------|
| [hayatky/xstash-cli](https://github.com/hayatky/xstash-cli) | CLI to sync X likes/bookmarks to local storage |
| [zylen97/twitter-bookmark-exporter](https://github.com/zylen97/twitter-bookmark-exporter) | Export via Chrome DevTools Protocol |

### Indie Hacker Monitoring Sources

Beyond personal saves, indie hackers typically monitor:

| Source | What to Collect | Method |
|--------|----------------|--------|
| **Hacker News** | Front page, new stories, Ask HN, Show HN | HN Firebase API |
| **Product Hunt** | New products, launches | PH API v2 or RSS |
| **Indie Hackers** | New stories, popular discussions | RSS |
| **Reddit** | Subreddits (r/SaaS, r/indiebiz, r/startups) | Reddit API |
| **Tech blogs** | New posts (Vercel, Stripe, etc.) | RSS feeds |
| **ArXiv** | New papers | ArXiv API |
| **YouTube** | Saved/watch-later | YouTube Data API v3 |

## Architectural Patterns Considered

### Pattern 1: Obsidian-Native (Direct to Vault)

```
Sources → collectors → _inbox/bookmarks/<date>.md
                               ↓
                        wiki-ingest → wiki/*
```

- **Pros:** Zero extra infra, leverages existing wiki-ingest, vault IS the memory
- **Cons:** No mobile capture for non-API sources (Threads, Instagram, random URLs)
- **Vault constitution alignment:** `_inbox/` is THE intake door (law 2). `_raw/` intentionally absent.
- **Verdict:** Recommended initially, but has mobile capture gap

### Pattern 2: Karakeep + Vault Sync

```
Phone share → Karakeep mobile app (one tap)
API sources → collector scripts → Karakeep API
                    ↓
            export_to_vault.py → _inbox/ → wiki-ingest → wiki/*
```

- **Pros:** One-tap mobile share from any app, auto-crawl, auto-tagging, idempotent API, dedup built-in
- **Cons:** Requires Docker (app + PostgreSQL + Meilisearch), another system to maintain
- **Verdict:** Better daily experience if user primarily uses phone. Being explored next.

### Pattern 3: Pure Telegram Workaround

```
Phone share → Telegram Saved Messages
                    ↓
            telegram_reader.py → _inbox/ → wiki-ingest → wiki/*
```

- **Pros:** No Docker, Telegram already on phone
- **Cons:** 2-tap share (extra step vs Karakeep's 1-tap), no auto-crawl
- **Verdict:** Simpler to start, less convenient daily

### Pattern 4: Direct JSON + Hermes-Only

```
Sources → collectors → bookmark_feed.json
                              ↓
                      Hermes cron → analysis
```

- **Pros:** Trivial to start
- **Cons:** No persistence, no Obsidian integration
- **Verdict:** Was prototyping approach, superseded by vault-native patterns

## User Context

- **Vault:** `source` at `C:\Users\chobi\Documents\source` — Karpathy-style LLM Wiki
- **Constitution:** 11 laws in AGENTS.md — `_inbox/` is sole intake door, `_raw/` absent
- **Co-managed by:** Claude Code (via AGENTS.md import in CLAUDE.md) + Hermes Agent
- **Primary device:** Phone — reads and bookmarks on mobile
- **Platform:** Windows 10 (desktop), Hermes Desktop app
- **Decision:** User chose **Pattern 1 (Obsidian-Native)** but with Karakeep under consideration for mobile capture

## Next Steps (User's Current Focus)

> "I will start with exploring Karakeep."

1. **Explore Karakeep** — run it locally, evaluate mobile app, test API
2. **Decide** — Karakeep vs Telegram for mobile capture
3. **Build collector project** — `bookmark-collector/` at `C:\Users\chobi\Projects\`
4. **Create Hermes skill** — `bookmark-collector` skill for agent context
5. **Add AGENTS.md operations** — bookmark collection entry in constitution
6. **Set up Hermes cron** — daily collection + wiki-ingest pipeline

## Key Architecture Decisions (So Far)

| Decision | Resolution |
|----------|-----------|
| **Memory layer** | Obsidian vault (`_inbox/` → wiki-ingest → `wiki/`) |
| **Mobile capture** | TBD — exploring Karakeep |
| **Collectors as skills?** | No — local Python scripts. Hermes skill = instruction manual only |
| **Dedup** | `seen_urls.json` (or Karakeep built-in) |
| **Content fetch** | trafilatura (or Karakeep auto-crawl) |
| **Cron scheduler** | Hermes cron job |
| **Docker needed?** | Only if Karakeep chosen |