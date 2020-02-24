import asyncio
import aiohttp
from aiohttp import web
import os
from heedy import Plugin
import signal
import json
import logging
import aiosqlite
import uuid

from manager import Manager

logging.basicConfig(level=logging.DEBUG)
l = logging.getLogger("notebook")

p = Plugin()


config_file = os.path.join(p.config['plugin_dir'], 'jupyter_heedy_config.py')
ipy_config = os.path.join(p.config['plugin_dir'], 'ipynb')


routes = web.RouteTableDef()

schema = """
CREATE TABLE notebook_cells (
    object_id VARCHAR NOT NULL,

    cell_id VARCHAR NOT NULL,
    cell_index INTEGER NOT NULL,

    cell_type STRING NOT NULL DEFAULT 'code',
    source VARCHAR NOT NULL DEFAULT '',
    outputs VARCHAR NOT NULL DEFAULT '[]',
    metadata VARCHAR NOT NULL DEFAULT '{}',

    PRIMARY KEY (object_id,cell_id),

    CONSTRAINT valid_outputs CHECK (json_valid(outputs) AND json_type(outputs)='array'),
    CONSTRAINT valid_metadata CHECK (json_valid(metadata) AND json_type(metadata)='object'),

    CONSTRAINT notebook_object
        FOREIGN KEY(object_id)
        REFERENCES objects(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
"""

sqldb = p.config["config"]["sql"]
if not sqldb.startswith("sqlite3://"):
    raise "Notebook plugin currently only supports sqlite"
sqldb = os.path.abspath(sqldb[10:].split("?")[0])
l.debug(f"Using database at {sqldb}")


def connect_to_database():
    return aiosqlite.connect(sqldb)


async def save_notebook_modifications(object_id,data):
    l.info(f"Updating notebook {object_id}")
    # object_id is the object to modify, and data is an *array* of cell modifications, which allows saving
    # the entire notebook at once, while maintaining ordering necessary for allowing cell index changes/inserts/deletes
    event_data = []

    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")

        for cell in data:
            
            if "delete" in cell and cell["delete"]:
                cell_id = cell["cell_id"]
                l.debug(f"Deleting cell {object_id}/{cell_id}")
                # On a cell delete, we need to shift indices of cells after it
                c = await db.execute("SELECT cell_index FROM notebook_cells WHERE object_id=? AND cell_id=?;", (object_id, cell_id))
                cell_index = int((await c.fetchone())[0])
                await c.close()

                await db.execute("DELETE FROM notebook_cells WHERE object_id=? AND cell_id=?;", (object_id, cell_id))
                await db.execute("UPDATE notebook_cells SET cell_index=cell_index-1 WHERE object_id=? AND cell_index>?", (object_id, cell_index))

                await db.execute("DELETE FROM notebook_cells WHERE object_id=? AND cell_id=?;", (object_id, cell_id))
                event_data.append({
                    "event": "notebook_cell_delete",
                    "object": object_id,
                    "data": {
                        "cell_id": cell_id,
                        "cell_index": cell_index
                    }
                })
            else:
                # Now we want to find out if we want to create or update a cell. We create a new cell if there is no cell_id,
                # or if the given cell_id does not exist yet
                id_exists = "cell_id" in cell
                if id_exists:
                    c = await db.execute("SELECT cell_id FROM notebook_cells WHERE object_id=? AND cell_id=?;", (object_id, cell["cell_id"]))
                    if (await c.fetchone()) is None:
                        id_exists = False
                    await c.close()
                    

                # Read the cell 
                if not id_exists:
                    cell_id = None
                    if "cell_id" in cell:
                        cell_id = cell["cell_id"]
                    else:
                        cell_id = uuid.uuid4().hex
                    l.debug(f"Creating new cell {object_id}/{cell_id}")

                    # First, get the max index
                    c = await db.execute("SELECT COALESCE(max(cell_index),-1) FROM notebook_cells WHERE object_id=?;", (object_id,))
                    maxindex = int((await c.fetchone())[0])
                    await c.close()

                    index = -1
                    if "cell_index" in cell:
                        index = cell["cell_index"]

                    if index == -1 or index > maxindex + 1:
                        # If appending to the end
                        index = maxindex + 1
                    elif index <= maxindex:
                        # We are inserting a cell somewhere in the middle of the document. Update the indices of all intermediate cells
                        await db.execute("UPDATE notebook_cells SET cell_index=cell_index+1 WHERE object_id=? AND cell_index>=?", (object_id, index))
                    
                    # Prepare the insert query
                    source = ""
                    metadata = {}
                    cell_type = "code"
                    if "source" in cell:
                        source = cell["source"]
                    if "metadata" in cell:
                        metadata = cell["metadata"]
                    if "cell_type" in cell:
                        cell_type = cell["cell_type"]
                    await db.execute("INSERT INTO notebook_cells (object_id,cell_id,cell_index,source,metadata,cell_type) VALUES (?,?,?,?,?,?)", (object_id, cell_id, index, source,json.dumps(metadata),cell_type))
                    
                    event_data.append({
                        "event": "notebook_cell_update",
                        "object": object_id,
                        "data": {
                            "cell_id": cell_id,
                            "source": source,
                            "cell_index": index,
                            "metadata": metadata,
                            "cell_type": cell_type
                        }
                    })
                else:
                    cell_id = cell["cell_id"]
                    l.debug(f"Updating cell {object_id}/{cell_id}")

                    setme = ""
                    outputs = []
                    if "source" in cell:
                        setme = "source=?"
                        outputs.append(cell["source"])
                    if "metadata" in cell:
                        if setme != "":
                            setme += ","
                        setme += "metadata=?"
                        outputs.append(json.dumps(cell["metadata"]))
                    if "cell_type" in cell:
                        if setme != "":
                            setme += ","
                        setme += "cell_type=?"
                        outputs.append(cell["cell_type"])

                    outputs.append(object_id)
                    outputs.append(cell_id)

                    if setme!="":
                        await db.execute(f"UPDATE notebook_cells SET {setme} WHERE object_id=? AND cell_id=?;", outputs)

                    # Next, prepare the event
                    c = await db.execute("SELECT source,metadata,cell_type,cell_index FROM notebook_cells WHERE object_id=? AND cell_id=?;", (object_id, cell_id))
                    row = (await c.fetchone())
                    await c.close()
                    cur_index = int(row[3])
                    
                    event_data.append({
                        "event": "notebook_cell_update",
                        "object": object_id,
                        "data": {
                            "cell_id": cell_id,
                            "source": row[0],
                            "metadata": json.loads(row[1]),
                            "cell_type": row[2],
                            "cell_index": cur_index
                        }
                    })

                    # Finally, check if there was an index change, and perform the necessary modifications
                    if "cell_index" in cell and cell["cell_index"]!=cur_index:
                        target_index = cell["cell_index"]
                        c = await db.execute("SELECT max(cell_index) FROM notebook_cells WHERE object_id=?;", (object_id,))
                        max_index = (await c.fetchone())[0]
                        await c.close()

                        if target_index<0 or target_index > max_index:
                            target_index = max_index

                        if target_index!=cur_index:
                            if target_index > cur_index:
                                await db.execute("UPDATE notebook_cells SET cell_index=cell_index-1 WHERE object_id=? AND cell_index >? AND cell_index<=?;", (object_id,cur_index,target_index))
                            else:
                                await db.execute("UPDATE notebook_cells SET cell_index=cell_index+1 WHERE object_id=? AND cell_index >=? AND cell_index<?;", (object_id,target_index,cur_index))
                            await db.execute("UPDATE notebook_cells SET cell_index=? WHERE object_id=? AND cell_id=?;", (target_index,object_id,cell_id))
                            # Update the event to include the correct index
                            event_data[-1]["data"]["cell_index"] = target_index
        await db.commit()

    # Fires the event, which includes source content (source content is assumed to be relatively small)
    for evt in event_data:
        await p.fire(evt)


async def notebook_cell_outputs(object_id, cell_id, data):
    l.debug(f"Updating outputs for {object_id}/{cell_id}")

    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        await db.execute("UPDATE notebook_cells SET outputs=json_insert(outputs,'$[' || json_array_length(outputs) || ']',json(?)) WHERE object_id=? AND cell_id=?;", (json.dumps(data), object_id, cell_id))
        await db.commit()

    await p.fire({
        "event": "notebook_cell_output",
        "object": object_id,
        "data": {
            "cell_id": cell_id
        }
    })


async def notebook_cell_output_clear(object_id, cell_id):
    l.debug(f"Clearing outputs for {object_id}/{cell_id}")

    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        await db.execute("UPDATE notebook_cells SET outputs='[]' WHERE object_id=? AND cell_id=?;", (object_id, cell_id))
        await db.commit()

    await p.fire({
        "event": "notebook_cell_output",
        "object": object_id,
        "data": {
            "cell_id": cell_id
        }
    })


async def read_notebook(object_id):
    l.debug(f"Reading notebook {object_id}")
    notebook = []
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        # First, get the max index
        async with db.execute("SELECT cell_id,cell_index,source,outputs,metadata,cell_type FROM notebook_cells WHERE object_id=? ORDER BY cell_index ASC;", (object_id,)) as cursor:
            async for row in cursor:
                notebook.append({
                    "cell_id": row[0],
                    "cell_index": row[1],
                    "source": row[2],
                    "outputs": json.loads(row[3]),
                    "metadata": json.loads(row[4]),
                    "cell_type": row[5]
                })
    return notebook

async def read_cell(object_id,cell_id):
    l.debug(f"Reading cell {object_id}/{cell_id}")
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        # First, get the max index
        async with db.execute("SELECT cell_id,cell_index,source,outputs,metadata,cell_type FROM notebook_cells WHERE object_id=? AND cell_id=?", (object_id,cell_id)) as cursor:
            async for row in cursor:
                return {
                    "cell_id": row[0],
                    "cell_index": row[1],
                    "source": row[2],
                    "outputs": json.loads(row[3]),
                    "metadata": json.loads(row[4]),
                    "cell_type": row[5]
                }


async def kernel_state_update(object_id,state):
    await p.fire({
        "event": "notebook_kernel_state",
        "object": object_id,
        "data": {
            "state": state
        }
    })

async def kernel_cell_output(object_id,cell_id,data):
    await notebook_cell_outputs(object_id,cell_id,data)

m = Manager(p, config_file, ipy_config,kernelStateChange=kernel_state_update,kernelOutput=kernel_cell_output)



@routes.get("/notebook")
async def notebook(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    return web.json_response(await read_notebook(r["object"]))


@routes.post("/notebook")
async def update_notebook(request):
    if not p.hasAccess(request, "write"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    data = await request.json()
    #try:
    await save_notebook_modifications(r["object"], data)
    return web.json_response("ok")
    #except Exception as e:
    #    l.error(str(e))
    #    return web.Response(status=500, body=str(e))

@routes.get("/notebook/cell/{cellid}")
async def get_cell(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)

    cell_content = await read_cell(r["object"],request.match_info['cellid'])
    
    return web.json_response(cell_content)

@routes.post("/notebook/kernel")
async def run_cell(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    data = await request.json()
    cell_content = await read_cell(r["object"],data['cell_id'])
    #print(cell_content,data["source"])
    if cell_content["source"]!=data["source"]:
        l.error("Cell source does not match")
        return web.Response(status=403, body="Source does not match")
    src = cell_content["source"]
    l.info(f"RUN {src}")
    await notebook_cell_output_clear(r["object"],data["cell_id"])
    server = await m.get(r["owner"])
    kernel = await server.kernel(r["object"])
    await kernel.run(data["cell_id"],src)
    return web.json_response("ok")

@routes.delete("/notebook/kernel")
async def close_kernel(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    
    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    await server.close_kernel(r["object"])
    
    return web.json_response("ok")

@routes.patch("/notebook/kernel")
async def interrupt_kernel(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    
    r = p.objectRequest(request)
    server = await m.get(r["owner"])
    await server.interrupt_kernel(r["object"])
    
    return web.json_response("ok")


@routes.get("/notebook/kernel")
async def kernel_state(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    
    r = p.objectRequest(request)

    if "start" in request.rel_url.query:
        server = await m.get(r["owner"])
        kernel = await server.kernel(r["object"])

        return web.json_response(kernel.state)
    
    if not r["owner"] in m.servers:
        return web.json_response("off")
    server = await m.get(r["owner"])
    return web.json_response(await server.state(r["object"]))

"""



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
                await ws_to.close(source=ws_to.close_source, message=msg.extra)
            else:
                raise ValueError(
                    'unexpected message type: %s', pprint.pformat(msg))

        # keep forwarding websocket data in both directions
    await asyncio.wait([ws_forward(ws_server, ws_client), ws_forward(ws_client, ws_server)], return_when=asyncio.FIRST_COMPLETED)

    return ws_client


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



"""

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

    # Make sure the notebook cells table exists
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        hastable = True
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notebook_cells';") as cursor:
            if await cursor.fetchone() is None:
                hastable = False
        if not hastable:
            await db.execute(schema)
        await db.commit()

    # Runs the server over a unix domain socket. The socket is automatically placed in the data folder,
    # and not the plugin folder.
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.UnixSite(runner, path=f"{p.name}.sock")
    await site.start()
    l.info("Notebook plugin ready")


asyncio.ensure_future(runme())
asyncio.get_event_loop().run_forever()
