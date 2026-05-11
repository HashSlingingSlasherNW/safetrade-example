import manager
import asyncio

yourAPIkey = "<your_api_key>"
yourAPISecret = "<your_secret_key>"
baseURL = "https://safe.trade/api/v2"
trackedMarket = "cpayusdt"
publicChannels = ["global.tickers", f"{trackedMarket}.depth", f"{trackedMarket}.trades"]

safetrade = manager.SafeTrade(baseURL, yourAPIkey, yourAPISecret, tracked_markets = [trackedMarket])

async def websocket_run():
  print(f"Following ticker: {trackedMarket.upper()}")
  safetrade.subscribe("public", publicChannels)
  await safetrade.run()

  while True:
    await asyncio.sleep(1)

if __name__ == "__main__":
  asyncio.run(websocket_run())
