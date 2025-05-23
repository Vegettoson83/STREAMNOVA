from aiohttp import web
import json
from pathlib import Path
import os
import aiohttp_cors

DB_PATH = Path("db/streamnova_all.json")

LANG_FLAGS = {
    "en": "🇺🇸", "es": "🇪🇸", "fr": "🇫🇷", "de": "🇩🇪",
    "jp": "🇯🇵", "pt": "🇧🇷", "it": "🇮🇹", "ar": "🇸🇦"
}

async def manifest_handler(request):
    manifest = {
        "id": "org.streamnova.addon",
        "version": "1.0.1",
        "name": "Stream Nova",
        "description": "Auto-scraping multi-source streaming addon with language flags",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [
            {"type": "movie", "id": "all", "name": "Stream Nova Movies"},
            {"type": "series", "id": "all", "name": "Stream Nova Series"}
        ],
        "idPrefixes": ["streamnova_"]
    }
    return web.json_response(manifest)

async def catalog_handler(request):
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    req_type = request.match_info["type"]
    metas = []

    for i, item in enumerate(db):
        if item.get("type", "movie") != req_type:
            continue
        flag = LANG_FLAGS.get(item.get("lang", "en").lower(), "")
        metas.append({
            "id": f"streamnova_{i}" if req_type == "movie"
                 else f"{item['series_id']}:{item['season']}:{item['episode']}",
            "type": req_type,
            "name": f"{flag} {item['title']}",
            "poster": "",
            "description": f"Source: {item['source'].capitalize()}, Lang: {item['lang'].upper()}"
        })
    return web.json_response({"metas": metas})

async def stream_handler(request):
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    stream_id = request.match_info['id']

    if ':' in stream_id:
        # Handle series: series_id:season:episode
        series_id, season, episode = stream_id.split(":")
        season = int(season)
        episode = int(episode)

        for entry in db:
            if (entry.get("type") == "series" and
                entry.get("series_id") == series_id and
                int(entry.get("season", 0)) == season and
                int(entry.get("episode", 0)) == episode):
                
                flag = LANG_FLAGS.get(entry.get("lang", "en").lower(), "")
                return web.json_response({
                    "streams": [{
                        "title": entry['title'],
                        "url": entry['url'],
                        "name": f"{flag} {entry['lang'].upper()} | {entry['source']}"
                    }]
                })
    else:
        # Fallback for movies: streamnova_#
        index = int(stream_id.replace("streamnova_", ""))
        entry = db[index]
        flag = LANG_FLAGS.get(entry.get("lang", "en").lower(), "")
        return web.json_response({
            "streams": [{
                "title": entry['title'],
                "url": entry['url'],
                "name": f"{flag} {entry['lang'].upper()} | {entry['source']}"
            }]
        })

    return web.json_response({"streams": []})  # Not found fallback

app = web.Application()
app.router.add_get("/manifest.json", manifest_handler)
app.router.add_get("/catalog/{type}/{id}.json", catalog_handler)
app.router.add_get("/stream/{type}/{id}.json", stream_handler)

# Enable CORS
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
})
for route in list(app.router.routes()):
    cors.add(route)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7000))
    web.run_app(app, port=port)
