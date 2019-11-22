import sys
import os
import asyncio
import socket
import time
import logging
import aiohttp
import json
from contextlib import closing


def free_port():
    # https://stackoverflow.com/questions/1365265/on-localhost-how-do-i-pick-a-free-port-number
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


async def wait_until_open(port):
    timeout = 20.0
    while timeout > 0:
        try:
            r, w = await asyncio.open_connection("localhost", port)
            w.close()
            await w.wait_closed()
            return
        except:
            timeout -= 0.1
            await asyncio.sleep(0.1)


class Server:
    _log = logging.getLogger("notebook.Server")

    def __init__(self, folder, port, headers):
        self.port = port
        self.folder = folder
        self.headers = headers
        self.s = aiohttp.ClientSession()
        self.url = f"http://localhost:{self.port}/api"

    async def create(self, oid):
        self._log.debug("Creating notebook %s", oid)
        # Create the holding directory
        try:
            os.makedirs(os.path.join(self.folder, oid))
        except:
            pass

        res = await self.s.put(f"{self.url}/contents/{oid}/notebook.ipynb", data=json.dumps({
            "type": "notebook"
        }), headers=self.headers)

        if res.status != 201:
            raise Exception("Could not create notebook")
        return

    async def contents(self, oid):
        self._log.debug("Reading notebook %s", oid)
        nbloc = f"{self.url}/contents/{oid}/notebook.ipynb"
        res = await self.s.get(nbloc, headers=self.headers)
        if res.status == 404:
            # The notebook doesn't exist - create it, and the read again
            await self.create(oid)
            res = await self.s.get(nbloc, headers=self.headers)
        return res.content

    async def save(self, oid, contents):
        self._log.debug("Saving notebook %s", oid)
        try:
            os.makedirs(os.path.join(self.folder, oid))
        except:
            pass
        nbloc = f"{self.url}/contents/{oid}/notebook.ipynb"
        res = await self.s.put(nbloc, headers=self.headers, data=json.dumps({
            "type": "notebook",
            "content": contents}))
        if res.status != 200 and res.status != 201:
            raise Exception("Cound not save notebook")
        return

    async def session(self, oid):
        self._log.debug("Reading session for %s", oid)
        res = await self.s.post(f"{self.url}/sessions", headers=self.headers, data=json.dumps({
            "path": f"{oid}/notebook.ipynb",
            "type": "notebook",
            "kernel": {"name": "python3"}
        }))
        return res.content

    async def kernel(self, oid):
        sess = json.loads(await (await self.session(oid)).read())
        kid = sess["kernel"]["id"]
        sid = sess["id"]
        self._log.debug("Opening kernel websocket for %s", oid)
        return await self.s.ws_connect(f"{self.url}/kernels/{kid}/channels?session_id={sid}", headers=self.headers)

    async def close(self):
        await self.s.close()


class Manager:
    _log = logging.getLogger("notebook.Manager")

    def __init__(self, plugin, config_file, ipy_config_dir, python=sys.executable):
        self.python = python
        self.config_file = config_file
        self.ipydir = ipy_config_dir
        self.p = plugin
        self.notebook_dir = os.path.join(
            self.p.config['data_dir'], 'notebooks')

        self.servers = {}
        self.closing = False

    async def get(self, username):
        # Return an existing server if it was already initialized
        if username in self.servers:
            # The server could be in process of initializing, so wait on the event
            await self.servers[username]["event"].wait()
            return self.servers[username]["server"]

        # Set the initialization event that can be waited by other requests
        self.servers[username] = {
            "event": asyncio.Event(),
        }

        # Get the access token from the plugin
        papps = await self.p.listApps(owner=username, plugin=self.p.name +
                                      ":" + "notebook", token=True)

        access_token = papps[0]["access_token"]
        port = free_port()
        notebook_dir = os.path.join(self.notebook_dir, username)
        try:
            os.makedirs(notebook_dir)
        except:
            pass

        penv = os.environ.copy()
        penv["HEEDY_ACCESS_TOKEN"] = access_token
        penv["IPYTHONDIR"] = self.ipydir
        self._log.debug(f"Starting server for {username} on port {port}")
        proc = await asyncio.create_subprocess_exec(self.python, "-m", "jupyter", "notebook",
                                                    f"--config={self.config_file}",
                                                    f"--NotebookApp.notebook_dir={notebook_dir}",
                                                    f"--NotebookApp.port={port}",
                                                    env=penv)
        if self.closing:
            proc.terminate()
        else:
            self.servers[username]["proc"] = proc

        await wait_until_open(port)

        self.servers[username]["server"] = Server(
            notebook_dir, port, {'Authorization': 'Token todoChangeMeBeforeRelease'})

        self._log.debug(f"Server for {username} ready")

        self.servers[username]["event"].set()
        return self.servers[username]["server"]

    async def close(self):
        self._log.debug("Terminating all servers")
        self.closing = True
        for k in self.servers:
            if "proc" in self.servers[k]:
                self.servers[k]["proc"].terminate()

        self._log.debug("Waiting for servers to exit")
        for k in self.servers:
            if "proc" in self.servers[k]:
                await self.servers[k]["proc"].wait()
            if "server" in self.servers[k]:
                await self.servers[k]["server"].close()
        self._log.debug("Notebook servers closed.")
