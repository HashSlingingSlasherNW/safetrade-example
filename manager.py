import api
from decimal import Decimal, InvalidOperation
import wsstore
import ticker

class SafeTrade:
  def __init__(self, base_url, key, secret, tracked_markets=None):
    self.base_url = base_url
    self.client = api.Client(base_url, key, secret)
    self._ws = None
    self.tickers = {}
    self.order_books = {}
    self.recent_trades = {}
    self.tracked_markets = set(market.lower() for market in (tracked_markets or []))

  @property
  def ws(self):
    if self._ws is None:
      self._ws = wsstore.WebsocketStore(self.base_url, self.client.get_authentication(), self.callback)
    return self._ws

  def callback(self, data):
    for channel, payload in self.iter_channels(data):
      if channel == "global.tickers":
        self.update_tickers(payload)
      elif channel.endswith(".depth") or channel.startswith("depth."):
        market = self.get_market_from_channel(channel, payload, "depth")
        if market is not None:
          self.update_order_book(market, payload)
      elif channel.endswith(".trades") or channel.startswith("trades."):
        market = self.get_market_from_channel(channel, payload, "trades")
        if market is not None:
          self.update_trades(market, payload)

  def iter_channels(self, data):
    if not isinstance(data, dict):
      return []

    if "stream" in data and "data" in data:
      return [(self.normalize_channel(data["stream"]), data["data"])]

    if "channel" in data and "data" in data:
      return [(self.normalize_channel(data["channel"]), data["data"])]

    if "method" in data and "params" in data:
      method = self.normalize_channel(data["method"])
      params = data["params"]

      if method == "global.tickers":
        if isinstance(params, dict) and "data" in params:
          return [("global.tickers", params["data"])]
        return [("global.tickers", params)]

      if method.endswith(".depth") or method == "depth":
        return [(self.build_channel_name(params, "depth"), params)]

      if method.endswith(".trades") or method == "trades":
        return [(self.build_channel_name(params, "trades"), params)]

    channels = []
    for key, value in data.items():
      if key in ("event", "status", "success", "message", "id", "result"):
        continue
      channels.append((self.normalize_channel(key), value))
    return channels

  def build_channel_name(self, payload, suffix):
    market = self.extract_market(payload)
    if market is None:
      return suffix
    return f"{market}.{suffix}"

  def normalize_channel(self, channel):
    if not isinstance(channel, str):
      return ""
    return channel.lower()

  def extract_market(self, payload):
    if isinstance(payload, dict):
      for key in ("market", "symbol", "pair"):
        market = payload.get(key)
        if isinstance(market, str):
          return self.normalize_market_name(market)
      if "data" in payload:
        return self.extract_market(payload["data"])
    return None

  def get_market_from_channel(self, channel, payload, suffix):
    if channel.endswith(f".{suffix}"):
      return channel[:-(len(suffix) + 1)]
    if channel.startswith(f"{suffix}."):
      return self.normalize_market_name(channel[(len(suffix) + 1):])
    return self.extract_market(payload)

  def update_tickers(self, payload):
    if not isinstance(payload, dict):
      return

    for market, market_data in payload.items():
      if not isinstance(market_data, dict):
        continue

      normalized_market = self.normalize_market_name(market)
      self.tickers[normalized_market] = ticker.Ticker(
        market_data.get("amount"),
        market_data.get("avg_price"),
        market_data.get("high"),
        market_data.get("last"),
        market_data.get("low"),
        market_data.get("open"),
        market_data.get("price_change_percent"),
        market_data.get("volume")
      )

      if normalized_market in self.tracked_markets:
        print(self.format_market_report(normalized_market))

  def update_order_book(self, market, payload):
    bids, asks = self.extract_order_book(payload)
    self.order_books[market] = {
      "bids": self.sort_levels(bids, reverse=True),
      "asks": self.sort_levels(asks),
      "timestamp": self.extract_timestamp(payload)
    }

    if market in self.tracked_markets:
      print(self.format_market_report(market))

  def update_trades(self, market, payload):
    trades = self.extract_trades(payload)
    if not trades:
      return

    self.recent_trades[market] = {
      "trades": trades,
      "timestamp": self.extract_timestamp(payload, trades)
    }

    if market in self.tracked_markets:
      print(self.format_market_report(market))

  def extract_order_book(self, payload):
    if isinstance(payload, dict) and "data" in payload:
      return self.extract_order_book(payload["data"])

    if not isinstance(payload, dict):
      return [], []

    bids = self.normalize_levels(payload.get("bids") or payload.get("buy") or [])
    asks = self.normalize_levels(payload.get("asks") or payload.get("sell") or [])
    return bids, asks

  def normalize_levels(self, levels):
    normalized_levels = []

    if isinstance(levels, dict):
      levels = list(levels.items())

    if not isinstance(levels, list):
      return normalized_levels

    for level in levels:
      price = None
      amount = None

      if isinstance(level, dict):
        price = level.get("price")
        amount = level.get("amount") or level.get("volume") or level.get("size")
      elif isinstance(level, (list, tuple)) and len(level) >= 2:
        price = level[0]
        amount = level[1]

      if price is None or amount is None:
        continue

      normalized_levels.append({
        "price": price,
        "amount": amount
      })

    return normalized_levels

  def extract_trades(self, payload):
    if isinstance(payload, dict):
      if "data" in payload:
        return self.extract_trades(payload["data"])
      if "trades" in payload:
        return self.extract_trades(payload["trades"])
      if payload.get("price") is not None:
        return [payload]
      return []

    if not isinstance(payload, list):
      return []

    normalized_trades = []
    for trade in payload:
      if not isinstance(trade, dict):
        continue
      if trade.get("price") is None:
        continue
      normalized_trades.append(trade)
    return normalized_trades

  def extract_timestamp(self, payload, items=None):
    if items:
      latest = self.get_latest_trade(items)
      if latest is not None:
        timestamp = latest.get("timestamp") or latest.get("created_at")
        if timestamp is not None:
          return timestamp

    if isinstance(payload, dict):
      for key in ("timestamp", "ts", "time", "created_at"):
        timestamp = payload.get(key)
        if timestamp is not None:
          return timestamp
      if "data" in payload:
        return self.extract_timestamp(payload["data"])
    return None

  def get_latest_trade(self, trades):
    latest_trade = None
    latest_timestamp = None

    for trade in trades:
      timestamp = trade.get("timestamp") or trade.get("created_at")
      if timestamp is None:
        latest_trade = trade
        continue
      if self.is_later_timestamp(timestamp, latest_timestamp):
        latest_trade = trade
        latest_timestamp = timestamp

    return latest_trade

  def format_market_report(self, market):
    sections = [self.format_ticker(market)]

    if market in self.order_books:
      sections.append(self.format_order_book(market))

    if market in self.recent_trades:
      sections.append(self.format_trades(market))

    return "\n".join(section for section in sections if section)

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

  def format_order_book(self, market):
    order_book = self.order_books.get(market)
    if order_book is None:
      return ""

    bids = order_book["bids"]
    asks = order_book["asks"]
    best_bid = self.get_level_price(bids)
    best_ask = self.get_level_price(asks)
    bid_depth = self.sum_amounts(bids)
    ask_depth = self.sum_amounts(asks)
    spread = self.calculate_spread(best_bid, best_ask)
    spread_percent = self.calculate_spread_percent(best_bid, best_ask)

    return (
      f"{market.upper()} order_book | best_bid={best_bid} best_ask={best_ask} "
      f"spread={spread} spread_pct={spread_percent} bid_depth={bid_depth} ask_depth={ask_depth} "
      f"bid_levels={len(bids)} ask_levels={len(asks)} timestamp={order_book['timestamp'] or 'n/a'}"
    )

  def format_trades(self, market):
    trade_state = self.recent_trades.get(market)
    if trade_state is None:
      return ""

    trades = trade_state["trades"]
    latest_trade = self.get_latest_trade(trades)
    buy_volume = self.sum_trade_amounts(trades, "buy")
    sell_volume = self.sum_trade_amounts(trades, "sell")
    total_volume = self.sum_trade_amounts(trades)
    average_price = self.calculate_average_trade_price(trades)
    side = self.get_trade_side(latest_trade)
    price = "n/a" if latest_trade is None else latest_trade.get("price", "n/a")

    return (
      f"{market.upper()} trades | count={len(trades)} last_price={price} last_side={side} "
      f"avg_trade_price={average_price} total_volume={total_volume} "
      f"buy_volume={buy_volume} sell_volume={sell_volume} "
      f"timestamp={trade_state['timestamp'] or 'n/a'}"
    )

  def sum_amounts(self, levels):
    total = Decimal("0")
    for level in levels:
      amount = self.to_decimal(level.get("amount"))
      if amount is not None:
        total += amount
    return self.format_decimal(total)

  def sum_trade_amounts(self, trades, side=None):
    total = Decimal("0")

    for trade in trades:
      trade_side = trade.get("side") or trade.get("type")
      if side is not None and (trade_side is None or str(trade_side).lower() != side):
        continue

      amount = self.to_decimal(trade.get("amount") or trade.get("volume") or trade.get("size"))
      if amount is not None:
        total += amount

    return self.format_decimal(total)

  def calculate_average_trade_price(self, trades):
    total_notional = Decimal("0")
    total_amount = Decimal("0")

    for trade in trades:
      price = self.to_decimal(trade.get("price"))
      amount = self.to_decimal(trade.get("amount") or trade.get("volume") or trade.get("size"))
      if price is None or amount is None:
        continue

      total_notional += price * amount
      total_amount += amount

    if total_amount == 0:
      return "n/a"
    return self.format_decimal(total_notional / total_amount)

  def calculate_spread(self, best_bid, best_ask):
    bid = self.to_decimal(best_bid)
    ask = self.to_decimal(best_ask)
    if bid is None or ask is None or bid <= 0 or ask <= 0:
      return "n/a"
    return self.format_decimal(ask - bid)

  def calculate_spread_percent(self, best_bid, best_ask):
    bid = self.to_decimal(best_bid)
    ask = self.to_decimal(best_ask)
    if bid is None or ask is None or bid <= 0 or ask <= 0:
      return "n/a"
    return f"{self.format_decimal(((ask - bid) / ask) * Decimal('100'))}%"

  def sort_levels(self, levels, reverse=False):
    return sorted(levels, key=self.level_sort_key, reverse=reverse)

  def normalize_market_name(self, market):
    return "".join(character for character in str(market).lower() if character.isalnum())

  def is_later_timestamp(self, timestamp, latest_timestamp):
    if latest_timestamp is None:
      return True

    timestamp_value = self.to_decimal(timestamp)
    latest_timestamp_value = self.to_decimal(latest_timestamp)

    if timestamp_value is not None and latest_timestamp_value is not None:
      return timestamp_value > latest_timestamp_value

    return str(timestamp) > str(latest_timestamp)

  def to_decimal(self, value):
    try:
      if value is None:
        return None
      return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
      return None

  def level_sort_key(self, level):
    price = self.to_decimal(level.get("price"))
    if price is None:
      return Decimal("0")
    return price

  def get_trade_side(self, trade):
    if trade is None:
      return "n/a"
    return trade.get("side") or trade.get("type") or "n/a"

  def get_level_price(self, levels):
    for level in levels:
      price = level.get("price")
      if self.to_decimal(price) is not None:
        return price
    return "n/a"

  def format_decimal(self, value):
    if value is None:
      return "n/a"

    normalized = format(value, "f")
    if "." in normalized:
      normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"

  def subscribe(self, type, channel):
    self.ws.subscribe(type, channel)

  def unsubscribe(self, type, channel):
    self.ws.unsubscribe(type, channel)

  def run(self):
    self.ws.run()
