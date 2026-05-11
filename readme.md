# SafeTrade WebSocket Client

This is an example Python project that helps clients connect to the SafeTrade Cryptocurrency Exchange WebSocket via Python.

## Requirements

- Python 3.7 or higher
- pip (Python package installer)

## Step-by-Step Setup

1. Clone the repository and move into the project folder:

```sh
git clone https://github.com/safetrade-exchange/example-client.git
cd example-client
```

2. (Optional) Create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
```

3. Install the required packages:

```sh
pip install -r requirements.txt
```

4. Open `/home/runner/work/safetrade-example/safetrade-example/main.py` and review the sample configuration:

```python
yourAPIkey = "<your_api_key>"
yourAPISecret = "<your_secret_key>"
base_url = "https://safe.trade/api/v2"
trackedMarket = "cpayusdt"
publicChannels = ["global.tickers", f"{trackedMarket}.depth", f"{trackedMarket}.trades"]
```

5. Update the values if needed:
   - Leave the API key and secret as placeholders if you only want public market data.
   - Change `trackedMarket` if you want to follow a different market.
   - Keep `publicChannels` aligned with the selected market so ticker, depth, and trade updates are all subscribed.

6. Start the client:

```sh
python main.py
```

7. Watch the output in your terminal.

The sample client is configured to follow the public `CPAY/USDT` market and print ticker values, order-book depth, and recent trade metrics as updates arrive.

## Project Structure
- api.py: Contains the Client class for interacting with the SafeTrade API.
- main.py: Entry point of the application.
- manager.py: Contains the SafeTrade class that manages WebSocket connections and subscriptions.
- ticker.py: Contains the Ticker class for handling ticker data.
- ws.py: Contains the Websocket class for managing WebSocket connections.
- wsstore.py: Contains the WebsocketStore class for managing multiple WebSocket connections.
