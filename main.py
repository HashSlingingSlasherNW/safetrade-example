import manager
import threading

yourAPIkey = "<your_api_key>"
yourAPISecret = "<your_secret_key>"
base_url = "https://safe.trade/api/v2"
trackedMarket = "cpayusdt"
publicChannels = ["global.tickers", f"{trackedMarket}.depth", f"{trackedMarket}.trades"]

safetrade = manager.SafeTrade(base_url, yourAPIkey, yourAPISecret, tracked_markets=[trackedMarket])

def websocket_run():
  print(f"Following ticker: {trackedMarket.upper()}")
  try:
    safetrade.subscribe("public", publicChannels)
    safetrade.run()
    threading.Event().wait()
  except KeyboardInterrupt:
    print("Stopping the CPAY ticker stream.")
  except Exception as error:
    print(f"Unable to start the CPAY ticker stream: {error}")

if __name__ == "__main__":
  websocket_run()
