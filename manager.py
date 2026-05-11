import api
import wsstore
import ticker

class SafeTrade:
  def __init__(self, baseURL, key, secret, tracked_markets=None):
    self.baseURL = baseURL
    self.client = api.Client(baseURL, key, secret)
    self._ws = None
    self.tickers = {}
    self.tracked_markets = set(market.lower() for market in (tracked_markets or []))

  @property
  def ws(self):
    if self._ws is None:
      self._ws = wsstore.WebsocketStore(self.baseURL, self.client.get_authentication(), self.callback)
    return self._ws

  def callback(self, data):
    for keyData in data:
      if keyData == "global.tickers":
        for market in data[keyData]:
          marketData = data[keyData][market]

          self.tickers[market] = ticker.Ticker(
            marketData["amount"],
            marketData["avg_price"],
            marketData["high"],
            marketData["last"],
            marketData["low"],
            marketData["open"],
            marketData["price_change_percent"],
            marketData["volume"]
          )

          if market in self.tracked_markets:
            print(self.format_ticker(market))

  def format_ticker(self, market):
    tracked_ticker = self.tickers.get(market)
    if tracked_ticker is None:
      return f"{market.upper()} ticker data is not available yet."

    return (
      f"{market.upper()} | last={tracked_ticker.last} open={tracked_ticker.open} "
      f"high={tracked_ticker.high} low={tracked_ticker.low} avg={tracked_ticker.avg_price} "
      f"change={tracked_ticker.price_change_percent}% volume={tracked_ticker.volume} "
      f"traded_amount={tracked_ticker.amount}"
    )

  def subscribe(self, type, channel):
    self.ws.subscribe(type, channel)

  def unsubscribe(self, type, channel):
    self.ws.unsubscribe(type, channel)

  def run(self):
    self.ws.run()
