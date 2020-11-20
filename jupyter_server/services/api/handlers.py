"""Tornado handlers for api specifications."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
from logging import Formatter, StreamHandler
import logging
from ipython_genutils.py3compat import cast_unicode

from tornado.websocket import WebSocketHandler
from traitlets.config.configurable import LoggingConfigurable
from jupyter_server.base.zmqhandlers import WebSocketMixin
import os

from tornado import web

from ...base.handlers import JupyterHandler, APIHandler
from jupyter_server.utils import ensure_async
from jupyter_server._tz import utcfromtimestamp, isoformat


class APISpecHandler(web.StaticFileHandler, JupyterHandler):

    def initialize(self):
        web.StaticFileHandler.initialize(self, path=os.path.dirname(__file__))

    @web.authenticated
    def get(self):
        self.log.warning("Serving api spec (experimental, incomplete)")
        return web.StaticFileHandler.get(self, 'api.yaml')

    def get_content_type(self):
        return 'text/x-yaml'


class APIStatusHandler(APIHandler):

    _track_activity = False

    @web.authenticated
    async def get(self):
        # if started was missing, use unix epoch
        started = self.settings.get('started', utcfromtimestamp(0))
        started = isoformat(started)

        kernels = await ensure_async(self.kernel_manager.list_kernels())
        total_connections = sum(k['connections'] for k in kernels)
        last_activity = isoformat(self.application.last_activity())
        model = {
            'started': started,
            'last_activity': last_activity,
            'kernels': len(kernels),
            'connections': total_connections,
        }
        self.finish(json.dumps(model, sort_keys=True))

class CustomLogger(StreamHandler):
    def __init__(self, callback):
        StreamHandler.__init__(self)
        self.setLevel(logging.INFO)
        self.setFormatter(Formatter('DUDE %(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)

class LoggerWebSocketHandler(WebSocketMixin, WebSocketHandler, JupyterHandler):
    def pre_get(self):
        """Run before finishing the GET request
        """
        # authenticate the request before opening the websocket
        if self.get_current_user() is None:
            self.log.warning("Couldn't authenticate WebSocket connection")
            raise web.HTTPError(403)

        if self.get_argument('session_id', False):
            self.session.session = cast_unicode(self.get_argument('session_id'))
        else:
            self.log.warning("No session ID specified")

    # self.write_message to reply
    # self.on_message to listen
    # one of these will be created when the connection is created I think
    # How does more than one client connect?
    async def get(self):
        # Do a pre_get to authenticate
        self.pre_get()

        # Add logger
        self.logger = CustomLogger(self.on_log)
        self.log.addHandler(self.logger)

        # Handle the base get
        res = super(LoggerWebSocketHandler, self).get()
        await res

    def on_close(self):
        self.log.removeHandler(self.logger)

    def on_log(self, msg):
        # Same format as a stream stdout
        model = {
            'header': {
                'msg_type': 'stream'
            },
            'content': {
                'text': msg
            }
        }
        self.write_message(json.dumps(model, sort_keys=True))



default_handlers = [
    (r"/api/spec.yaml", APISpecHandler),
    (r"/api/status", APIStatusHandler),
    (r"/api/logger", LoggerWebSocketHandler)
]
