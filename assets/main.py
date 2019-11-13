import asyncio
import aiohttp
from aiohttp import web
import os
from heedy import Plugin
import signal
import json
import pprint
p = Plugin()

routes = web.RouteTableDef()

notebook_dir = os.path.join(p.config['data_dir'], 'notebooks')

try:
    os.makedirs(notebook_dir)
except:
    pass

headers = {'Authorization': 'Token mytoken'}


@routes.get("/contents")
async def contents(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    # r = await request.json()
    sr = p.sourceRequest(request)
    nbloc = f"http://localhost:8887/api/contents/{sr['owner']}/{sr['source']}/notebook.ipynb"

    res = await s.get(nbloc, headers=headers)

    if res.status == 404:
        print("CREATE")
        try:
            os.makedirs(os.path.join(notebook_dir, sr['owner'], sr['source']))
        except:
            pass
        # We need to create the notebook
        res = await s.put(nbloc, data=json.dumps({
            # "name": "notebook.ipynb",
            # "path": os.path.join(notebook_dir, sr['owner'], sr['source']),
            "type": "notebook"
        }), headers=headers)
        if res.status != 201:
            web.Response(status=500, text=json.dumps(
                {"error": "Internal error"}))
        res = await s.get(nbloc, headers=headers)
        if res.status != 200:
            web.Response(status=500, text=json.dumps(
                {"error": "Internal error"}))
            print(await res.text())

    return web.Response(text=await res.text())


@routes.get("/session")
async def session(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    sr = p.sourceRequest(request)
    nbp = f"{sr['owner']}/{sr['source']}/notebook.ipynb"
    res = await s.post("http://localhost:8887/api/sessions", headers=headers, data=json.dumps({
        "path": nbp,
        "type": "notebook",
        "kernel": {"name": "python3"}
    }))

    return web.Response(text=await res.text())


@routes.get("/kernel")
async def kernel(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    sr = p.sourceRequest(request)

    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    nbp = f"{sr['owner']}/{sr['source']}/notebook.ipynb"
    res = await s.post("http://localhost:8887/api/sessions", headers=headers, data=json.dumps({
        "path": nbp,
        "type": "notebook",
        "kernel": {"name": "python3"}
    }))
    resj = await res.json()
    kid = resj["kernel"]["id"]
    sid = resj["id"]
    print("Started kernel", kid)
    async with s.ws_connect(
        f"http://localhost:8887/api/kernels/{kid}/channels?session_id={sid}", headers=headers
    ) as ws_server:

        async def ws_forward(ws_from, ws_to):
            async for msg in ws_from:
                #logger.info('>>> msg: %s',pprint.pformat(msg))
                mt = msg.type
                md = msg.data
                if mt == aiohttp.WSMsgType.TEXT:
                    await ws_to.send_str(md)
                elif mt == aiohttp.WSMsgType.BINARY:
                    await ws_to.send_bytes(md)
                elif mt == aiohttp.WSMsgType.PING:
                    await ws_to.ping()
                elif mt == aiohttp.WSMsgType.PONG:
                    await ws_to.pong()
                elif ws_to.closed:
                    await ws_to.close(code=ws_to.close_code, message=msg.extra)
                else:
                    raise ValueError(
                        'unexpected message type: %s', pprint.pformat(msg))

        # keep forwarding websocket data in both directions
        await asyncio.wait([ws_forward(ws_server, ws_client), ws_forward(ws_client, ws_server)], return_when=asyncio.FIRST_COMPLETED)

        return ws_client


app = web.Application()
app.add_routes(routes)


s = None
proc = None


async def shutdown():
    global proc, s
    print("Shutting down")
    if proc is not None:
        print("Killing")
        proc.terminate()
        # proc.send_signal(signal.SIGINT)
        # proc.send_signal(signal.SIGINT)
        await proc.wait()

    await app.shutdown()
    await app.cleanup()
    await s.close()
    print("DONE")
    asyncio.get_event_loop().stop()


async def runme():
    global proc, notebook_dir, s
    s = aiohttp.ClientSession()
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda sig=sig: asyncio.create_task(shutdown()))

    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "jupyter", "notebook", f"--config={os.path.join(p.config['plugin_dir'],'jupyter_heedy_config.py')}", f"--NotebookApp.notebook_dir={notebook_dir}")
    #
    # Starts the jupyter server

    # Runs the server over a unix domain socket. The socket is automatically placed in the data folder,
    # and not the plugin folder.
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.UnixSite(runner, path=f"{p.name}.sock")
    await site.start()
    print("Notebook Plugin Ready")


asyncio.ensure_future(runme())
asyncio.get_event_loop().run_forever()
