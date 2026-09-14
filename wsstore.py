import ws
import threading

class WebsocketStore:
  def __init__(self, base_url, header=None, callback=None):
    self.base_url = base_url
    self.header = header
    self.callback = callback
    self.public = None
    self.private = None

  def get_socket(self, type, create_socket=True):
    if create_socket and type == "public" and self.public is None:
      self.public = ws.Websocket(self.base_url, "public", None, self.callback)
    elif create_socket and type == "private" and self.private is None:
      self.private = ws.Websocket(self.base_url, "private", self.header, self.callback)

    if type == "public":
      return self.public
    if type == "private":
      return self.private
    return None

  def subscribe(self, type, channel):
    socket = self.get_socket(type)
    if socket is not None:
      socket.subscribe(channel)

  def unsubscribe(self, type, channel):
    socket = self.get_socket(type, create_socket=False)
    if socket is not None:
      socket.unsubscribe(channel)

  def run(self):
    threads = [self.build_listener_thread(socket) for socket in (self.public, self.private) if socket is not None]

    for thread in threads:
      thread.start()

  def build_listener_thread(self, socket):
    return threading.Thread(target=socket.onMessage, daemon=True)
