---
title: Fetching the GitHub API from Python, with a fallback to gh
slug: urllib-gh-api-fallback
date: 2026-11-13
tags: ["Python", "Networking", "GitHub"]
summary: FastGithub terminates TLS in the middle, Python's certifi bundle rejects its certificate, and the safe fix is a fallback to gh api on certificate errors only — not disabling verification.
---

The star counts on this site's homepage are fetched by a script that runs before the build. The first version used only `urllib.request`. It worked locally — until I turned on FastGithub (a DNS hijack plus local reverse proxy that speeds up GitHub access).

The error was `CERTIFICATE_VERIFY_FAILED`. The reason isn't complicated: FastGithub terminates TLS in the middle, and its certificate lives in the **Windows certificate store**. Go programs like `gh` read that store, so they're fine; Python's `urllib` uses its bundled `certifi` bundle, which doesn't contain the certificate.

## Don't fix it by disabling verification

The first instinct is `ssl._create_unverified_context()`. It runs, but it turns off certificate checking for everything — if someone later swaps a certificate in the middle, the script won't notice. And the script has to run in GitHub Actions, where machine-specific workarounds don't apply.

## Fall back to gh's transport

`gh api <url>` prints GitHub's raw JSON, which makes it a usable fallback channel:

```python
def api(url):
    try:
        return _via_urllib(url)
    except Exception as e:
        if 'CERTIFICATE' in str(e) or 'SSL' in str(e):
            return _via_gh(url)   # subprocess: gh api <url>
        raise
```

Only *certificate* errors fall back; everything else raises as usual. In Actions the request goes through urllib (fast, no dependency), and locally behind the MITM proxy it goes through `gh` (which reuses the system store). The code is the same either way.

A side benefit: `gh` is already authenticated, so local runs don't have to worry about the anonymous API's 60-requests-per-hour limit.

## Don't let a failed fetch break the build

The data script is part of the build. A network hiccup shouldn't take down the whole deployment. So on failure it **prints a warning, keeps the previous JSON, and exits 0**:

```python
except urllib.error.HTTPError as e:
    print('GitHub API %s: %s (keeping previous data)' % (e.code, e.reason))
    return                      # exit 0 on purpose; keep CI green
except Exception as e:
    print('%s: %s (keeping previous data)' % (type(e).__name__, e))
    return
```

⚠️ Do **not** write `sys.exit('...')` here: `sys.exit` with a string argument exits with code **1**, which fails the CI step and defeats the whole point. If you genuinely want a non-zero exit, call `sys.exit(1)` explicitly somewhere it is intended, and make sure the caller can handle it.

The numbers on the page are a day old, but the site still ships. For data that is nice-to-have rather than essential, stale beats broken.
