import aiohttp.web
from . import app, CONFIG

host = CONFIG['ap']['host']
note = CONFIG['note']

async def default(request):
    return aiohttp.web.Response(
        status=200,
        content_type="text/html",
        charset="utf-8",
        text="""
<html><head>
 <title>ActivityPub Relay at {host}</title>
 <style>
  p {{ color: #FFFFFF; font-family: monospace, arial; font-size: 100%; }}
  body {{ background-color: #000000; }}
  </style>
</head>
<body>
<p>This is an Activity Relay for fediverse instances.</p>
<p>{note}</p>
<p>For Mastodon instances, you may subscribe to this relay with the address: <a href="https://{host}/inbox">https://{host}/inbox</a></p>
<p>For Pleroma and other instances, you may subscribe to this relay with the address: <a href="https://{host}/actor">https://{host}/actor</a></p>
<p>To host your own relay, you may download the code at this address: <a href="https://git.pleroma.social/pleroma/relay">https://git.pleroma.social/pleroma/relay</a></p>
</body></html>

""".format(host=host, note=note))

app.router.add_get('/', default)
