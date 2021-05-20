# BassieBot MegaBot client a la creme
import sys
import socket
import json

# Constants
ROBOT_ID = len(sys.argv) >= 2 and int(sys.argv[1]) or 1

SERVER_PORT = 8080

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
    { "id": 1, "x": 1, "y": 1, "directions": [], "connected": False },
    { "id": 2, "x": MAP_WIDTH - 2, "y": 1, "directions": [], "connected": False },
    { "id": 3, "x": 1, "y": MAP_HEIGHT - 2, "directions": [], "connected": False },
    { "id": 4, "x": MAP_WIDTH - 2, "y": MAP_HEIGHT - 2, "directions": [], "connected": False }
]

# TCP socket connection with the server
print("[ROBOT " + str(ROBOT_ID) + "] Connecting with the communication server at 127.0.0.1:" + str(SERVER_PORT) + "...")
with socket.socket() as client:
    try:
        client.connect(("127.0.0.1", SERVER_PORT))
    except:
        print("[ROBOT " + str(ROBOT_ID) + "] Can't connect with the communication server")
        exit()

    # Send register message
    client.sendall(bytearray(json.dumps({
        "type": "connect",
        "data": {
            "id": ROBOT_ID
        }
    }), "UTF-8"))
    robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
    robot["connected"] = True
    print("[ROBOT " + str(ROBOT_ID) + "] Robot " + str(ROBOT_ID) + " connected")

    while data := client.recv(1024):
        print("[ROBOT " + str(ROBOT_ID) + "] Server message: " + data.decode())
        message = json.loads(data)

        if message["type"] == "connect":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)
            robot["connected"] = True
            print("[ROBOT " + str(ROBOT_ID) + "] Robot " + str(robot["id"]) + " is connected")

        if message["type"] == "disconnect":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)
            robot["connected"] = False
            print("[ROBOT " + str(ROBOT_ID) + "] Robot " + str(robot["id"]) + " is disconnected")

        if message["type"] == "direction":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)
            robot["directions"].append({
                "x": message["data"]["x"],
                "y": message["data"]["y"]
            })

        if message["type"] == "tick":
            if len(directions_queue) > 0:
                # Calculate path

                # Do step

                # Send response
                pass

        if message["type"] == "tick_done":
            if message["data"]["id"] != ROBOT_ID:
                robot = next((robot for robot in robots if robot["id"] == message["data"]["id"]), None)
                robot["x"] = message["data"]["position"]["x"]
                robot["y"] = message["data"]["position"]["y"]

                for mapUpdate in message["data"]["map"]:
                    map[mapUpdate["y"] * MAP_WIDTH + mapUpdate["x"]] = mapUpdate["type"]
