import ws
import threading

class WebsocketStore:
  def __init__(self, baseURL, header = None, callback = None):
    self.baseURL = baseURL
    self.header = header
    self.callback = callback
    self.public = None
    self.private = None

  def get_socket(self, type):
    if type == "public" and self.public is None:
      self.public = ws.Websocket(self.baseURL, "public", None, self.callback)
    elif type == "private" and self.private is None:
      self.private = ws.Websocket(self.baseURL, "private", self.header, self.callback)

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
    socket = self.public if type == "public" else self.private if type == "private" else None
    if socket is not None:
      socket.unsubscribe(channel)

  async def run(self):
    threads = []

    if self.public is not None:
      threads.append(threading.Thread(target=self.public.onMessage, daemon = True))
    if self.private is not None:
      threads.append(threading.Thread(target=self.private.onMessage, daemon = True))

    for thread in threads:
      thread.start()
