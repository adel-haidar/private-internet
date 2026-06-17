"""Server-rendered public share page with Open Graph / Twitter Card meta.

Served straight from FastAPI at /api/share/{token} (already proxied to the API
by nginx + CloudFront), so social crawlers get rich previews and humans without
an account can view the shared item directly. Calm-Intelligence styled, inline
CSS only (self-contained — no SPA, no external assets besides the media itself).
"""

from html import escape

from private_internet.config import get_settings


def _meta(prop: str, content: str, *, name: bool = False) -> str:
    if not content:
        return ""
    attr = "name" if name else "property"
    return f'<meta {attr}="{escape(prop)}" content="{escape(content)}">'


def render_share_html(snapshot: dict, share_url: str) -> str:
    s = get_settings()
    site = s.base_url
    title = snapshot.get("title") or s.app_name
    description = snapshot.get("description") or ""
    image = snapshot.get("image_url") or ""
    media_type = snapshot.get("media_type") or "text"
    media_url = snapshot.get("media_url") or ""
    kicker = snapshot.get("kicker") or ""
    subtitle = snapshot.get("subtitle") or ""
    body = snapshot.get("body") or ""

    # Open Graph + Twitter Card. Video uses og:video; everything else a large image.
    og = [
        _meta("og:type", "video.other" if media_type == "video" else "article"),
        _meta("og:site_name", s.app_name),
        _meta("og:title", title),
        _meta("og:description", description),
        _meta("og:url", share_url),
        _meta("og:image", image),
        _meta("twitter:title", title, name=True),
        _meta("twitter:description", description, name=True),
        _meta("twitter:image", image, name=True),
    ]
    if media_type == "video" and media_url:
        og += [
            _meta("og:video", media_url),
            _meta("og:video:secure_url", media_url),
            _meta("og:video:type", "video/mp4"),
            _meta("twitter:card", "player", name=True),
        ]
    elif media_type == "audio" and media_url:
        og += [
            _meta("og:audio", media_url),
            _meta("twitter:card", "summary_large_image", name=True),
        ]
    else:
        og += [_meta("twitter:card", "summary_large_image", name=True)]
    og_tags = "\n    ".join(t for t in og if t)

    # Body media block.
    if media_type == "video" and media_url:
        media_html = (
            f'<video class="media" controls playsinline '
            f'poster="{escape(image)}"><source src="{escape(media_url)}" '
            f'type="video/mp4"></video>'
        )
    elif media_type == "audio" and media_url:
        art = (
            f'<img class="media art" src="{escape(image)}" alt="">' if image else ""
        )
        media_html = (
            f'{art}<audio class="audio" controls src="{escape(media_url)}"></audio>'
        )
    elif image:
        media_html = f'<img class="media" src="{escape(image)}" alt="">'
    else:
        media_html = ""

    body_html = f'<p class="body">{escape(body)}</p>' if body else ""
    subtitle_html = f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ""
    kicker_html = f'<span class="kicker">{escape(kicker)}</span>' if kicker else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} · {escape(s.app_name)}</title>
    {og_tags}
    <style>
      :root {{ color-scheme: dark; }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0; min-height: 100vh; display: flex; align-items: center;
        justify-content: center; padding: 24px;
        background: radial-gradient(120% 120% at 50% 0%, #1a1832 0%, #0b0b14 60%);
        color: #e8e8f4;
        font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      }}
      .card {{
        width: 100%; max-width: 560px;
        background: #14141f; border: 1px solid #26263a; border-radius: 16px;
        overflow: hidden;
      }}
      .media {{ width: 100%; display: block; background: #0b0b14; }}
      .art {{ aspect-ratio: 1/1; object-fit: cover; }}
      .audio {{ width: 100%; display: block; padding: 16px 20px 0; }}
      .content {{ padding: 22px 24px 26px; }}
      .kicker {{
        font: 600 11px/1 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: 0.18em; color: #e8a444; text-transform: uppercase;
      }}
      h1 {{ font-size: 22px; line-height: 1.25; margin: 12px 0 4px; font-weight: 700; }}
      .subtitle {{ margin: 0 0 8px; color: #a8a8c0; font-size: 14px; }}
      .body {{ margin: 12px 0 0; color: #cfcfe0; font-size: 15px; line-height: 1.6;
               white-space: pre-wrap; }}
      .cta {{
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px; padding: 16px 24px; border-top: 1px solid #26263a;
        background: #101019;
      }}
      .cta span {{ color: #a8a8c0; font-size: 13px; }}
      .cta a {{
        background: #6b5cff; color: #fff; text-decoration: none; font-weight: 600;
        font-size: 14px; padding: 9px 16px; border-radius: 10px; white-space: nowrap;
      }}
    </style>
</head>
<body>
    <main class="card">
      {media_html}
      <div class="content">
        {kicker_html}
        <h1>{escape(title)}</h1>
        {subtitle_html}
        {body_html}
      </div>
      <div class="cta">
        <span>Made with {escape(s.app_name)}</span>
        <a href="{escape(site)}">Create your own →</a>
      </div>
    </main>
</body>
</html>"""


def render_unavailable_html() -> str:
    s = get_settings()
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link unavailable · {escape(s.app_name)}</title>
<style>
  body {{ margin:0; min-height:100vh; display:flex; align-items:center;
    justify-content:center; background:#0b0b14; color:#e8e8f4;
    font-family: system-ui, sans-serif; text-align:center; padding:24px; }}
  a {{ color:#8b7cff; }}
</style></head>
<body><div>
  <h1>This link is no longer available</h1>
  <p>The share may have been revoked or never existed.</p>
  <p><a href="{escape(s.base_url)}">Go to {escape(s.app_name)}</a></p>
</div></body></html>"""
