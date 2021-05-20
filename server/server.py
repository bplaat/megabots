# MegaBots communication server
import socket
import json
import threading
import asyncio
import websockets

# Constants
SERVER_PORT = 8080
WEBSOCKETS_PORT = 8082

MAP_WIDTH = 16
MAP_HEIGHT = 16
TILE_UNKOWN = 0
TILE_NORMAL = 1
TILE_CHEST = 2
TILE_WALL = 3

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
        # Split maybe concated json messages
        messages = data.decode().split('}{')
        if len(messages) > 1:
            for i in range(len(messages)):
                if i == 0:
                    messages[i] = messages[i] + '}'
                elif i == len(messages) - 1:
                    messages[i] = '{' + messages[i]
                else:
                    messages[i] = '{' + messages[i] + '}'

        # Read every incomming json message
        for message in messages:
            print("[SERVER] Robot message: " + message)
            message = json.loads(message)

            # Connect message
            if message["type"] == "connect":
                robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                robot["connection"] = connection
                print("[SERVER] Robot " + str(robot["id"]) + " is connected")

                for otherRobot in robots:
                    if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                        # Send robot connect message of this other robot
                        robot["connection"].send(json.dumps({
                            "type": "connect",
                            "data": {
                                "robot_id": otherRobot["id"]
                            }
                        }).encode("utf8"))

                        # Send other robot connect message of this robot
                        otherRobot["connection"].send(json.dumps({
                            "type": "connect",
                            "data": {
                                "robot_id": robot["id"]
                            }
                        }).encode("utf8"))

            # New direction message
            if message["type"] == "new_direction":
                robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                robot["directions"].append({
                    "id": message["data"]["direction"]["id"],
                    "x": message["data"]["direction"]["x"],
                    "y": message["data"]["direction"]["y"]
                })

                for otherRobot in robots:
                    if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                        otherRobot["connection"].send(json.dumps({
                            "type": "new_direction",
                            "data": {
                                "robot_id": robot["id"],
                                "direction": {
                                    "id": message["data"]["direction"]["id"],
                                    "x": message["data"]["direction"]["x"],
                                    "y": message["data"]["direction"]["y"]
                                }
                            }
                        }).encode("utf8"))

            # Update direction message
            if message["type"] == "update_direction":
                robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                direction = next((direction for direction in robot["directions"] if direction["id"] == message["data"]["direction"]["id"]), None)
                direction["x"] = message["data"]["direction"]["x"]
                direction["y"] = message["data"]["direction"]["y"]

                for otherRobot in robots:
                    if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                        otherRobot["connection"].send(json.dumps({
                            "type": "update_direction",
                            "data": {
                                "robot_id": robot["id"],
                                "direction": {
                                    "id": message["data"]["direction"]["id"],
                                    "x": message["data"]["direction"]["x"],
                                    "y": message["data"]["direction"]["y"]
                                }
                            }
                        }).encode("utf8"))

            # Cancel direction message
            if message["type"] == "cancel_direction":
                robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                for i, direction in enumerate(robot["directions"]):
                    if direction["id"] == message["data"]["direction"]["id"]:
                        del robot["directions"][i]
                        break

                for otherRobot in robots:
                    if otherRobot["connection"] != None and otherRobot["id"] != robot["id"]:
                        otherRobot["connection"].send(json.dumps({
                            "type": "cancel_direction",
                            "data": {
                                "robot_id": robot["id"],
                                "direction": {
                                    "id": message["data"]["direction"]["id"]
                                }
                            }
                        }).encode("utf8"))

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
                    robot["connection"].send(json.dumps({
                        "type": "disconnect",
                        "data": {
                            "robot_id": robot["id"]
                        }
                    }).encode("utf8"))
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
                    "robot_id": robot["id"]
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
