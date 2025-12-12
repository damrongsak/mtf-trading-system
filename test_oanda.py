import v20
import time
import sys

TOKEN = "8cbc29b8f0208bb1b92c66ffb9a5f265-cd601bc5b06240aa8115cc036e01e873"
ACCOUNT_ID = "001-011-437083-005"
HOSTNAME = "stream-fxtrade.oanda.com"

def test_stream():
    print(f"Connecting to {HOSTNAME} with account {ACCOUNT_ID}...")
    ctx = v20.Context(
        hostname=HOSTNAME,
        port=443,
        token=TOKEN,
        datetime_format="RFC3339"
    )

    try:
        # Use a longer timeout or no timeout
        response = ctx.pricing.stream(
            ACCOUNT_ID,
            instruments="EUR_USD,XAU_USD",
            snapshot=True
        )
        
        print("Connected. Waiting for parts...")
        for msg_type, msg in response.parts():
            print(f"Received: {msg_type}")
            if msg_type == "pricing.Price":
                print(f"Price: {msg.instrument} {msg.bids[0].price} / {msg.asks[0].price}")
                break # Success!
                
            if msg_type == "pricing.Heartbeat":
                print("Heartbeat received.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stream()
