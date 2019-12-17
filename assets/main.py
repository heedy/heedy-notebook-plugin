import asyncio
import aiohttp
from aiohttp import web
import os
from heedy import Plugin
import signal
import json
import pprint
import logging

from jupyter import Manager

logging.basicConfig(level=logging.DEBUG)
l = logging.getLogger("notebook")

p = Plugin()

config_file = os.path.join(p.config['plugin_dir'], 'jupyter_heedy_config.py')
ipy_config = os.path.join(p.config['plugin_dir'], 'ipynb')
m = Manager(p, config_file, ipy_config)

routes = web.RouteTableDef()

schema = """
CREATE TABLE notebook_cells (
    objectid VARCHAR NOT NULL,
    cellid VARCHAR PRIMARY KEY,
    cellindex INTEGER NOT NULL,
    code VARCHAR NOT NULL,
    output VARCHAR NOT NULL DEFAULT '[]',

    CONSTRAINT valid_output CHECK (json_valid(output) AND json_type(output)='array'),

    CONSTRAINT notebook_object
        FOREIGN KEY(objectid)
        REFERENCES objects(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT nextcellid
        FOREIGN KEY(nextcell)
        REFERENCS notebook_cells(cellid)
        ON UPDATE CASCADE
        ON DELETE CASCADE

);
"""

def insert(tx,objectid, after,code):
    cellid = "newcelluuidv4"


    # Insert into data
    tx.exec("UPDATE notebooks SET output=json_insert(output,'$[' || json_array_length(output) || ']',?) WHERE cellid=?")
    tx.exec("INSERT INTO notebooks(objectid,cellid,nextcell,code,output) VALUES (?,)",objectid,cellid,v)

    # Need a trigger on insert at index i UPDATE where index > i, -> i+1. Same for removed cell (update index i -> i-1)
    # I can explicity do this in a transaction, or add a trigger to do it automatically on any insert
    tx.exec("UPDATE notebooks SET cellindex = cellindex+1 WHERE cellindex >= i AND objectid=?")
    tx.exec("INSERT INTO notebooks() ...")

    # Now append:
    tx.exec("INSERT INTO notebooks SET cellindex = (SELECT max(cellindex)+1 FROM notebooks where objectid=?)")

    # Finally delete
    tx.exec("UPDATE notebooks SET cellindex = cellindex-1 WHERE cellindex >= i AND objectid=?")
    tx.exec("DELETE FROM notebooks WHERE cellid=?")

def fireevent():
    p.fire("notebook_cell_update",objectid, cellid, index, code,cleardata : bool)
    p.fire("notebook_cell_create",objectid, cellid, index, code)
    p.fire("notebook_cell_delete")
    p.fire("notebook_cell_data",objectid, cellid, data)

@routes.get("/notebook")
async def notebook(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)

"""
@routes.get("/contents")
async def contents(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    contents = await server.contents(r["object"])

    sr = web.StreamResponse()
    sr.content_type = "application/json"
    await sr.prepare(request)
    async for data in contents.iter_any():
        await sr.write(data)
    await sr.write_eof()
    return sr


@routes.put("/contents")
async def contents(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    await server.save(r["object"], await request.json())
    return web.json_response({"response": "ok"})


@routes.get("/session")
async def session(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    contents = await server.session(r["object"])

    sr = web.StreamResponse()
    sr.content_type = "application/json"
    await sr.prepare(request)
    async for data in contents.iter_any():
        await sr.write(data)
    await sr.write_eof()
    return sr


@routes.get("/kernel")
async def kernel(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")

    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    ws_server = await server.kernel(r["object"])

    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

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


async def shutdown():
    l.info("Shutting down")
    await app.shutdown()
    await app.cleanup()
    await m.close()
    l.info("Closed")
    asyncio.get_event_loop().stop()


async def runme():
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda sig=sig: asyncio.create_task(shutdown()))

    # Runs the server over a unix domain socket. The socket is automatically placed in the data folder,
    # and not the plugin folder.
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.UnixSite(runner, path=f"{p.name}.sock")
    await site.start()
    l.info("Notebook plugin ready")


asyncio.ensure_future(runme())
asyncio.get_event_loop().run_forever()
"""