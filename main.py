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
from datetime import datetime

import manager

logging.basicConfig(level=logging.INFO)
l = logging.getLogger("notebook")

p = Plugin()


config_file = os.path.join(p.config["plugin_dir"], "jupyter_heedy_config.py")
ipy_config = os.path.join(p.config["plugin_dir"], "ipynb")


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


async def save_notebook_modifications(object_id, data):
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
                c = await db.execute(
                    "SELECT cell_index FROM notebook_cells WHERE object_id=? AND cell_id=?;",
                    (object_id, cell_id),
                )
                cell_index = int((await c.fetchone())[0])
                await c.close()

                await db.execute(
                    "DELETE FROM notebook_cells WHERE object_id=? AND cell_id=?;",
                    (object_id, cell_id),
                )
                await db.execute(
                    "UPDATE notebook_cells SET cell_index=cell_index-1 WHERE object_id=? AND cell_index>?",
                    (object_id, cell_index),
                )

                await db.execute(
                    "DELETE FROM notebook_cells WHERE object_id=? AND cell_id=?;",
                    (object_id, cell_id),
                )
                event_data.append(
                    {
                        "event": "notebook_cell_delete",
                        "object": object_id,
                        "data": {"cell_id": cell_id, "cell_index": cell_index},
                    }
                )
            else:
                # Now we want to find out if we want to create or update a cell. We create a new cell if there is no cell_id,
                # or if the given cell_id does not exist yet
                id_exists = "cell_id" in cell
                if id_exists:
                    c = await db.execute(
                        "SELECT cell_id FROM notebook_cells WHERE object_id=? AND cell_id=?;",
                        (object_id, cell["cell_id"]),
                    )
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
                    c = await db.execute(
                        "SELECT COALESCE(max(cell_index),-1) FROM notebook_cells WHERE object_id=?;",
                        (object_id,),
                    )
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
                        await db.execute(
                            "UPDATE notebook_cells SET cell_index=cell_index+1 WHERE object_id=? AND cell_index>=?",
                            (object_id, index),
                        )

                    # Prepare the insert query
                    source = ""
                    metadata = {}
                    cell_type = "code"
                    output = []
                    if "source" in cell:
                        source = cell["source"]
                    if "metadata" in cell:
                        metadata = cell["metadata"]
                    if "cell_type" in cell:
                        cell_type = cell["cell_type"]
                    if "outputs" in cell:
                        output = cell["outputs"]
                    await db.execute(
                        "INSERT INTO notebook_cells (object_id,cell_id,cell_index,source,metadata,cell_type,outputs) VALUES (?,?,?,?,?,?,?)",
                        (
                            object_id,
                            cell_id,
                            index,
                            source,
                            json.dumps(metadata),
                            cell_type,
                            json.dumps(output),
                        ),
                    )

                    event_data.append(
                        {
                            "event": "notebook_cell_update",
                            "object": object_id,
                            "data": {
                                "cell_id": cell_id,
                                "source": source,
                                "cell_index": index,
                                "metadata": metadata,
                                "cell_type": cell_type,
                            },
                        }
                    )

                    if "outputs" in cell and len(cell["outputs"]) > 0:
                        event_data.append(
                            {
                                "event": "notebook_cell_output",
                                "object": object_id,
                                "data": {"cell_id": cell_id},
                            }
                        )
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
                    if "outputs" in cell:
                        if setme != "":
                            setme += ","
                        setme += "outputs=?"
                        outputs.append(json.dumps(cell["outputs"]))

                    outputs.append(object_id)
                    outputs.append(cell_id)

                    if setme != "":
                        await db.execute(
                            f"UPDATE notebook_cells SET {setme} WHERE object_id=? AND cell_id=?;",
                            outputs,
                        )

                    # Next, prepare the event
                    c = await db.execute(
                        "SELECT source,metadata,cell_type,cell_index FROM notebook_cells WHERE object_id=? AND cell_id=?;",
                        (object_id, cell_id),
                    )
                    row = await c.fetchone()
                    await c.close()
                    cur_index = int(row[3])

                    event_data.append(
                        {
                            "event": "notebook_cell_update",
                            "object": object_id,
                            "data": {
                                "cell_id": cell_id,
                                "source": row[0],
                                "metadata": json.loads(row[1]),
                                "cell_type": row[2],
                                "cell_index": cur_index,
                            },
                        }
                    )

                    # Finally, check if there was an index change, and perform the necessary modifications
                    if "cell_index" in cell and cell["cell_index"] != cur_index:
                        target_index = cell["cell_index"]
                        c = await db.execute(
                            "SELECT max(cell_index) FROM notebook_cells WHERE object_id=?;",
                            (object_id,),
                        )
                        max_index = (await c.fetchone())[0]
                        await c.close()

                        if target_index < 0 or target_index > max_index:
                            target_index = max_index

                        if target_index != cur_index:
                            if target_index > cur_index:
                                await db.execute(
                                    "UPDATE notebook_cells SET cell_index=cell_index-1 WHERE object_id=? AND cell_index >? AND cell_index<=?;",
                                    (object_id, cur_index, target_index),
                                )
                            else:
                                await db.execute(
                                    "UPDATE notebook_cells SET cell_index=cell_index+1 WHERE object_id=? AND cell_index >=? AND cell_index<?;",
                                    (object_id, target_index, cur_index),
                                )
                            await db.execute(
                                "UPDATE notebook_cells SET cell_index=? WHERE object_id=? AND cell_id=?;",
                                (target_index, object_id, cell_id),
                            )
                            # Update the event to include the correct index
                            event_data[-1]["data"]["cell_index"] = target_index

                    if "outputs" in cell:
                        event_data.append(
                            {
                                "event": "notebook_cell_output",
                                "object": object_id,
                                "data": {"cell_id": cell_id},
                            }
                        )
        await db.commit()

    # Fires the event, which includes source content (source content is assumed to be relatively small)
    for evt in event_data:
        await p.fire(evt)


async def notebook_cell_outputs(object_id, cell_id, data):
    l.debug(f"Updating outputs for {object_id}/{cell_id}")

    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        await db.execute(
            "UPDATE notebook_cells SET outputs=json_insert(outputs,'$[' || json_array_length(outputs) || ']',json(?)) WHERE object_id=? AND cell_id=?;",
            (json.dumps(data), object_id, cell_id),
        )
        await db.commit()

    await p.fire(
        {
            "event": "notebook_cell_output",
            "object": object_id,
            "data": {"cell_id": cell_id},
        }
    )


async def notebook_cell_output_clear(object_id, cell_id):
    l.debug(f"Clearing outputs for {object_id}/{cell_id}")

    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        await db.execute(
            "UPDATE notebook_cells SET outputs='[]' WHERE object_id=? AND cell_id=?;",
            (object_id, cell_id),
        )
        await db.commit()

    await p.fire(
        {
            "event": "notebook_cell_output",
            "object": object_id,
            "data": {"cell_id": cell_id},
        }
    )


async def read_notebook(object_id):
    l.debug(f"Reading notebook {object_id}")
    notebook = []
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        # First, get the max index
        async with db.execute(
            "SELECT cell_id,cell_index,source,outputs,metadata,cell_type FROM notebook_cells WHERE object_id=? ORDER BY cell_index ASC;",
            (object_id,),
        ) as cursor:
            async for row in cursor:
                notebook.append(
                    {
                        "cell_id": row[0],
                        "cell_index": row[1],
                        "source": row[2],
                        "outputs": json.loads(row[3]),
                        "metadata": json.loads(row[4]),
                        "cell_type": row[5],
                    }
                )
    return notebook


async def read_cell(object_id, cell_id):
    l.debug(f"Reading cell {object_id}/{cell_id}")
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        # First, get the max index
        async with db.execute(
            "SELECT cell_id,cell_index,source,outputs,metadata,cell_type FROM notebook_cells WHERE object_id=? AND cell_id=?",
            (object_id, cell_id),
        ) as cursor:
            async for row in cursor:
                return {
                    "cell_id": row[0],
                    "cell_index": row[1],
                    "source": row[2],
                    "outputs": json.loads(row[3]),
                    "metadata": json.loads(row[4]),
                    "cell_type": row[5],
                }


async def kernel_state_update(object_id, state):
    try:
        # Trying to update state for an object that was deleted fails
        await p.fire(
            {
                "event": "notebook_kernel_state",
                "object": object_id,
                "data": {"state": state},
            }
        )
    except:
        pass


async def update_last_modified(r):
    cur_date = datetime.today().strftime("%Y-%m-%d")
    if r["last_modified"] != cur_date:
        l.debug(f"Updating modification time of {r['object']} to {cur_date}")
        await (await p.objects[r["object"]]).update(last_modified=cur_date)


async def kernel_cell_output(object_id, cell_id, data):
    await notebook_cell_outputs(object_id, cell_id, data)


m = manager.Manager(
    p,
    config_file,
    ipy_config,
    kernelStateChange=kernel_state_update,
    kernelOutput=kernel_cell_output,
)


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
    for d in data:
        if "outputs" in d and len(d["outputs"]) > 0:
            return web.Response(
                status=403, body="Setting non-empty outputs not permitted"
            )
    # try:
    await save_notebook_modifications(r["object"], data)
    await update_last_modified(r)
    return web.json_response("ok")
    # except Exception as e:
    #    l.error(str(e))
    #    return web.Response(status=500, body=str(e))


@routes.get("/notebook.ipynb")
async def ipynb_get(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")

    r = p.objectRequest(request)
    heedy_nb = await read_notebook(r["object"])

    cells = [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"collapsed": True},
            "source": manager.kernel_init_code,
            "outputs": [],
        }
    ]

    for c in heedy_nb:
        cell_metadata = {}
        curcell = {
            "cell_type": c["cell_type"],
            "execution_count": None,
            "metadata": {},
            "source": c["source"],
        }
        if c["cell_type"] == "code":
            curcell["metadata"] = {
                "collapsed": False
                if not "collapsed" in c["metadata"]
                else c["metadata"]["collapsed"],
                "scrolled": False
                if not "scrolled" in c["metadata"]
                else c["metadata"]["scrolled"],
            }
            curcell["outputs"] = c["outputs"]
        cells.append(curcell)

    ipython_notebook = {
        "metadata": {
            "kernel_info": {"name": "python3"},
            "language_info": {
                "name": "python",
                "mimetype": "text/x-python",
                "codemirror_mode": {"name": "ipython", "version": 3},
                "version": "3.7.3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 0,
        "cells": cells,
    }
    return web.Response(
        text=json.dumps(ipython_notebook),
        content_type="application/x-ipynb+json",
        headers={"Content-Disposition": "attachment"},
    )


@routes.post("/notebook.ipynb")
async def post_ipython(request):
    if not p.hasAccess(request, "write"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    data = json.loads((await request.post())["notebook"].file.read())
    # print(data)
    if data["metadata"]["language_info"]["name"] != "python":
        return web.Response(status=400, body="Notebook must be python")

    if len(data["cells"]) > 0:
        cells = []

        for c in data["cells"]:
            if isinstance(c["source"], list):
                c["source"] = "".join(c["source"])
            cur_cell = {
                "cell_type": c["cell_type"],
                "source": c["source"],
                "metadata": c["metadata"],
            }
            if "outputs" in c:
                cur_cell["outputs"] = c["outputs"]
            cells.append(cur_cell)

        if "HEEDY NOTEBOOK HEADER" in cells[0]["source"]:
            # Remove the heedy header
            cells = cells[1:]
        await save_notebook_modifications(r["object"], cells)
        await update_last_modified(r)

    return web.json_response("ok")


@routes.get("/notebook/cell/{cellid}")
async def get_cell(request):
    if not p.hasAccess(request, "read"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)

    cell_content = await read_cell(r["object"], request.match_info["cellid"])

    return web.json_response(cell_content)


@routes.post("/notebook/kernel")
async def run_cell(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")
    r = p.objectRequest(request)
    data = await request.json()
    cell_content = await read_cell(r["object"], data["cell_id"])
    # print(cell_content,data["source"])
    if cell_content["source"] != data["source"]:
        l.error("Cell source does not match")
        return web.Response(status=403, body="Source does not match")
    if cell_content["cell_type"] == "code":
        src = cell_content["source"]
        l.info(f"RUN {data['cell_id']}")
        await notebook_cell_output_clear(r["object"], data["cell_id"])
        server = await m.get(r["owner"], notify_oid=r["object"])
        kernel = await server.kernel(r["object"])
        await kernel.run(data["cell_id"], src)
    return web.json_response("ok")


@routes.delete("/notebook/kernel")
async def close_kernel(request):
    if not p.hasAccess(request, "run"):
        return web.Response(status=403, body="Not permitted")

    r = p.objectRequest(request)
    await m.close_kernel(r["owner"], r["object"])

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
        server = await m.get(r["owner"], notify_oid=r["object"])
        kernel = await server.kernel(r["object"])

        return web.json_response(kernel.state)

    if not r["owner"] in m.servers:
        return web.json_response("off")
    server = await m.get(r["owner"])
    return web.json_response(await server.state(r["object"]))


@routes.post("/notebook_delete")
async def notebook_deleted(request):
    evt = await request.json()
    l.debug(f"Notebook Deleted: {evt}")
    asyncio.create_task(m.close_kernel(evt["user"], evt["object"]))
    return web.Response(text="ok")


@routes.post("/user_delete")
async def notebook_deleted_user(request):
    evt = await request.json()
    l.debug(f"User Deleted: {evt}")
    asyncio.create_task(m.close_server(evt["user"]))
    return web.Response(text="ok")


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
        loop.add_signal_handler(sig, lambda sig=sig: asyncio.create_task(shutdown()))

    # Make sure the notebook cells table exists
    async with connect_to_database() as db:
        await db.execute("PRAGMA foreign_keys=1")
        hastable = True
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notebook_cells';"
        ) as cursor:
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
