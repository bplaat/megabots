# MegaBots communication server
import socket
import json
import threading
import asyncio
import websockets

# Constants
SERVER_PORT = 8080
WEBSOCKETS_PORT = 8082

MAP_WIDTH = 12
MAP_HEIGHT = 12
TILE_UNKOWN = 0
TILE_NORMAL = 1
TILE_WALL = 2

# Init square map with robots in corners and all around wall
map = [TILE_UNKOWN] * (MAP_HEIGHT * MAP_WIDTH)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        if x == 0 or y == 0 or x == MAP_WIDTH - 1 or y == MAP_HEIGHT - 1:
            map[y * MAP_WIDTH + x] = TILE_WALL
        if (
            (x == 1 and y == 1) or
            (x == MAP_WIDTH - 2 and y == 1) or
            (x == 1 and y == MAP_HEIGHT - 2) or
            (x == MAP_WIDTH - 2 and y == MAP_HEIGHT - 2)
        ):
            map[y * MAP_WIDTH + x] = TILE_NORMAL

# Robots start in the corners
robots = [
    { "id": 1, "x": 1, "y": 1, "directions": [], "connection": None },
    { "id": 2, "x": MAP_WIDTH - 2, "y": 1, "directions": [], "connection": None },
    { "id": 3, "x": 1, "y": MAP_HEIGHT - 2, "directions": [], "connection": None },
    { "id": 4, "x": MAP_WIDTH - 2, "y": MAP_HEIGHT - 2, "directions": [], "connection": None }
]

# Communications server
def handleRobotConnectionThread(connection):
    while data := connection.recv(1024):
        print("[SERVER] Robot message: " + data.decode())
        message = json.loads(data)

        # Connect message
        if message["type"] == "connect":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)

            robot["connection"] = connection
            print("[SERVER] Robot " + str(robot["id"]) + " is connected")

            for otherRobot in robots:
                if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                    otherRobot["connection"].sendall(bytearray(json.dumps({
                        "type": "connect",
                        "data": {
                            "id": robot["id"]
                        }
                    }), "UTF-8"))

        # Direction message
        if message["type"] == "direction":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)
            robot["directions"].append({
                "x": message["data"]["x"],
                "x": message["data"]["y"]
            })

            for otherRobot in robots:
                if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                    otherRobot["connection"].sendall(bytearray(json.dumps({
                        "type": "direction",
                        "data": {
                            "id": robot["id"],
                            "x": message["data"]["x"],
                            "y": message["data"]["y"]
                        }
                    }), "UTF-8"))

        # Tick done message
        if message["type"] == "tick_done":
            pass

    # Disconnect message
    for robot in robots:
        if robot["connection"] == connection:
            print("[SERVER] Robot " + str(robot["id"]) + " is disconnected")
            robot["connection"] = None

            for robot in robots:
                if robot["connection"] != None:
                    robot["connection"].sendall(bytearray(json.dumps({
                        "type": "disconnect",
                        "data": {
                            "id": robot["id"]
                        }
                    }), "UTF-8"))
            break

# Start communication server
def communicationServerThread():
    with socket.create_server(("127.0.0.1", SERVER_PORT)) as server:
        print("[SERVER] Communication server is listening at 127.0.0.1:" + str(SERVER_PORT))
        server.listen()
        while True:
            connection, address = server.accept()
            connectionThread = threading.Thread(target = handleRobotConnectionThread, args = (connection,))
            connectionThread.start()
communicationThread = threading.Thread(target = communicationServerThread)
communicationThread.start()

# Start websockets server
async def websocketsConnection(websocket, uri):
    print("[SERVER] Websockets connected")

    # Send connected message of all robots that all ready are connected
    for robot in robots:
        if robot["connection"] != None:
            await websocket.send(json.dumps({
                "type": "connect",
                "data": {
                    "id": robot["id"]
                }
            }))

    while True:
        try:
            data = await websocket.recv()
            print("[SERVER] Websockets message: " + data)
        except:
            print("[SERVER] Websockets disconnected")
            return

server = websockets.serve(websocketsConnection, "127.0.0.1", WEBSOCKETS_PORT)
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()
