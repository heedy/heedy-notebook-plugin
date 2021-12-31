import sys
import os
import asyncio
import socket
import time
import logging
import aiohttp
import json
from contextlib import closing
import pprint
import datetime
import uuid
from pathlib import Path


def free_port():
    # https://stackoverflow.com/questions/1365265/on-localhost-how-do-i-pick-a-free-port-number
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("localhost", 0))
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


# This code is run to initialize the kernel
kernel_init_code = (Path(__file__).parent / "notebook_header.py").read_text()


class Kernel:
    def __init__(
        self, session, url, headers, kernel_id, oid, state_update, output_update
    ):
        self.state = "starting"
        self.s = session
        self.url = url
        self.headers = headers
        self.id = kernel_id
        self.oid = oid
        self.q = asyncio.Queue()
        self.state_update = state_update
        self.output_update = output_update
        self._log = logging.getLogger(f"notebook.Server:{oid}")
        asyncio.create_task(self.websocket())

        self.ws = None
        self.ws_wait = asyncio.Event()

    async def close(self):
        su = self.state_update

        async def doNothing(x, y):
            pass

        self.state_update = doNothing
        await su(self.oid, "off")

        # This is to be called from server, since it doesn't remove the kernel from the server's kernel dict
        await self.s.delete(f"{self.url}/kernels/{self.id}", headers=self.headers)

    async def interrupt(self):
        await self.s.post(
            f"{self.url}/kernels/{self.id}/interrupt", headers=self.headers
        )

    async def run(self, cell_id, code):
        header = {
            "msg_id": cell_id + "_" + uuid.uuid4().hex,
            "session": self.oid,
            "date": datetime.datetime.now().isoformat(),
            "msg_type": "execute_request",
        }
        msg = {
            "header": header,
            "parent_header": header,
            "metadata": {
                "recordTiming": False,
                "deletedCells": [],
            },
            "channel": "shell",
            "buffers": [],
            "content": {
                "code": code,
                "silent": False,
                "allow_stdin": False,
                "stop_on_error": True,
                "store_history": True,
            },
        }
        if self.ws is None:
            await self.ws_wait.wait()
        await self.ws.send_str(json.dumps(msg))

    async def websocket(self):
        self._log.debug("Running websocket")
        ws = await self.s.ws_connect(
            f"{self.url}/kernels/{self.id}/channels?session_id={self.oid}",
            headers=self.headers,
        )

        # Send the initialization message
        header = {
            "msg_id": uuid.uuid4().hex,
            "session": self.oid,
            "date": datetime.datetime.now().isoformat(),
            "msg_type": "execute_request",
        }
        msg = {
            "header": header,
            "parent_header": header,
            "metadata": {
                "recordTiming": False,
                "deletedCells": [],
            },
            "channel": "shell",
            "buffers": [],
            "content": {
                "code": kernel_init_code,
                "silent": True,
                "allow_stdin": False,
                "stop_on_error": True,
                "store_history": True,
            },
        }
        await ws.send_str(json.dumps(msg))

        self.ws = ws
        self.ws_wait.set()

        # Continue processing messages
        async for msg in ws:
            # self._log.debug('>>> full_msg: %s',pprint.pformat(msg))
            mt = msg.type
            md = msg.data
            if mt == aiohttp.WSMsgType.TEXT:

                # Now see what type of message we got
                data = json.loads(md)
                self._log.debug(">>> msg: %s", pprint.pformat(data))
                msg_type = data["msg_type"]
                if msg_type == "status":
                    self.state = data["content"]["execution_state"]
                    self._log.debug(f"Kernel state: {self.state}")
                    await self.state_update(self.oid, self.state)
                elif msg_type in ["execute_result", "display_data", "stream", "error"]:
                    output = data["content"]
                    output["output_type"] = msg_type

                    # Get the cell ID
                    cell_id = data["parent_header"]["msg_id"].split("_")[0]
                    self._log.debug(f"Output {pprint.pformat(output)}")
                    await self.output_update(self.oid, cell_id, output)

            elif mt == aiohttp.WSMsgType.PING:
                await ws.pong()
            elif ws.closed:
                return
            else:
                raise ValueError("unexpected message type: %s", pprint.pformat(msg))


class Server:
    def __init__(
        self,
        folder,
        port,
        headers,
        username="",
        onStateChange=lambda x, y: print(x, y),
        onOutput=lambda x, y, z: print(x, y, z),
    ):
        self.port = port
        self.folder = folder
        self.headers = headers
        self.username = username
        self.onStateChange = onStateChange
        self.onOutput = onOutput
        self._log = logging.getLogger(f"notebook.Server:{username}")
        self.s = aiohttp.ClientSession()
        self.url = f"http://localhost:{self.port}/api"
        # The kernels
        self.kernels = {}

    async def kernel(self, oid):
        # Return an existing kernel if it is already running
        if oid in self.kernels:
            # Could be initializing the kernel, so wait on the event
            await self.kernels[oid]["event"].wait()
            if not oid in self.kernels:
                return self.kernel(oid)
            return self.kernels[oid]["kernel"]

        kernel_obj = {"event": asyncio.Event()}

        self.kernels[oid] = kernel_obj

        # Create a new kernel
        res = await self.s.post(
            f"{self.url}/kernels",
            headers=self.headers,
            data=json.dumps({"name": "python3"}),
        )
        kernel_response = await res.json()
        self._log.debug(f"Started kernel {kernel_response['id']} for {oid}")
        k = Kernel(
            self.s,
            self.url,
            self.headers,
            kernel_response["id"],
            oid,
            self.onStateChange,
            self.onOutput,
        )
        kernel_obj["kernel"] = k
        kernel_obj["event"].set()
        return k

        # self._log.debug("Opening kernel websocket for %s", oid)
        # return await self.s.ws_connect(f"{self.url}/kernels/{kid}/channels?session_id={sid}", headers=self.headers)

    async def close_kernel(self, oid):
        # Close a running kernel
        if not oid in self.kernels:
            return
        k = self.kernels[oid]
        del self.kernels[oid]
        await k["event"].wait()
        await k["kernel"].close()

    async def interrupt_kernel(self, oid):
        if not oid in self.kernels:
            return
        k = await self.kernel(oid)
        await k.interrupt()

    async def state(self, oid):
        if not oid in self.kernels:
            return "off"
        return (await self.kernel(oid)).state

    async def close(self):
        await self.s.close()


class Manager:
    _log = logging.getLogger("notebook.Manager")

    def __init__(
        self,
        plugin,
        config_file,
        ipy_config_dir,
        kernelStateChange=lambda x, y: print(x, y),
        kernelOutput=lambda x, y, z: print(x, y, z),
        python=sys.executable,
    ):
        self.executable = os.path.join(os.path.dirname(python), "jupyter-notebook")
        self.config_file = config_file
        self.ipydir = ipy_config_dir
        self.p = plugin
        self.kernelStateChange = kernelStateChange
        self.kernelOutput = kernelOutput
        self.notebook_dir = os.path.join(self.p.config["data_dir"], "notebooks")

        self.servers = {}
        self.closing = False

    async def get(self, username, notify_oid=None):
        # Return an existing server if it was already initialized
        if username in self.servers:
            # The server could be in process of initializing, so wait on the event
            await self.servers[username]["event"].wait()
            return self.servers[username]["server"]

        # Send a status for the notify_oid
        if notify_oid is not None:
            await self.kernelStateChange(notify_oid, "starting")

        # Set the initialization event that can be waited by other requests
        self.servers[username] = {
            "event": asyncio.Event(),
        }

        # Get the access token from the plugin
        papps = await self.p.apps(
            owner=username, plugin=self.p.name + ":" + "notebook", token=True
        )

        access_token = papps[0]["access_token"]
        port = free_port()
        notebook_dir = os.path.join(self.notebook_dir, username)
        try:
            os.makedirs(notebook_dir)
        except:
            pass

        penv = os.environ.copy()
        penv["HEEDY_ACCESS_TOKEN"] = access_token
        penv["HEEDY_SERVER_URL"] = self.p.config["config"]["api"]
        penv["IPYTHONDIR"] = self.ipydir
        self._log.debug(
            f"Starting server {self.executable} for {username} on port {port}"
        )
        proc = await asyncio.create_subprocess_exec(
            self.executable,
            f"--config={self.config_file}",
            f"--NotebookApp.notebook_dir={notebook_dir}",
            f"--NotebookApp.port={port}",
            "--allow-root",
            env=penv,
        )
        if self.closing:
            proc.terminate()
        else:
            self.servers[username]["proc"] = proc

        await wait_until_open(port)

        self.servers[username]["server"] = Server(
            notebook_dir,
            port,
            {"Authorization": "Token todoChangeMeBeforeRelease"},
            username=username,
            onStateChange=self.kernelStateChange,
            onOutput=self.kernelOutput,
        )

        self._log.debug(f"Server for {username} ready")

        self.servers[username]["event"].set()
        return self.servers[username]["server"]

    async def close_server(self, k):
        if k in self.servers:
            ss = self.servers[k]
            del self.servers[k]
            if "proc" in ss:
                ss["proc"].terminate()
                await ss["proc"].wait()

            if "server" in ss:
                await ss["server"].close()

    async def close_kernel(self, username, oid):
        if username in self.servers:
            serv = await self.get(username)
            await serv.close_kernel(oid)

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
