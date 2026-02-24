import os
from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor

appClientId = os.getenv("CTRADER_CLIENT_ID")
appClientSecret = os.getenv("CTRADER_CLIENT_SECRET")

if not appClientId or not appClientSecret:
    print("Error: CTRADER_CLIENT_ID or CTRADER_CLIENT_SECRET environment variables not set.")
    exit(1)

# Try Demo first
host = EndPoints.PROTOBUF_DEMO_HOST
port = EndPoints.PROTOBUF_PORT

print(f"Connecting to {host}:{port}...")

client = Client(host, port, TcpProtocol)

def onError(failure):
    print("Message Error: ", failure)
    reactor.stop()

def connected(client):
    print("Connected to server")
    print("Sending Application Auth Request...")
    request = ProtoOAApplicationAuthReq()
    request.clientId = appClientId
    request.clientSecret = appClientSecret
    deferred = client.send(request)
    deferred.addErrback(onError)

def disconnected(client, reason):
    print("Disconnected: ", reason)
    try:
        reactor.stop()
    except:
        pass

def onMessageReceived(client, message):
    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
        print("SUCCESS: API Application authorized!")
        reactor.stop()
    elif message.payloadType == ProtoOAErrorRes().payloadType:
        print("ERROR: Received Error Response")
        print(Protobuf.extract(message))
        reactor.stop()
    else:
        # print("Message received: ", message.payloadType)
        pass

client.setConnectedCallback(connected)
client.setDisconnectedCallback(disconnected)
client.setMessageReceivedCallback(onMessageReceived)
client.startService()

# Stop after 10 seconds if nothing happens
reactor.callLater(10, reactor.stop)
print("Starting Reactor...")
reactor.run()
