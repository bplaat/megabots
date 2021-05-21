#!/usr/bin/env python

import sys
import asyncio
import websockets
import json

# Constants
WEBSOCKETS_PORT = 8080

ROBOT_ID = len(sys.argv) >= 2 and int(sys.argv[1]) or 1

MAP_WIDTH = 16
MAP_HEIGHT = 16

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
TILE_WALL = 3

# Init square map with robots in corners and all around wall with some chest stripes inside
map = [TILE_UNKOWN] * (MAP_HEIGHT * MAP_WIDTH)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        if x == 0 or y == 0 or x == MAP_WIDTH - 1 or y == MAP_HEIGHT - 1:
            map[y * MAP_WIDTH + x] = TILE_WALL
        elif (
            (x == 1 and y == 1) or
            (x == MAP_WIDTH - 2 and y == 1) or
            (x == 1 and y == MAP_HEIGHT - 2) or
            (x == MAP_WIDTH - 2 and y == MAP_HEIGHT - 2)
        ):
            map[y * MAP_WIDTH + x] = TILE_FLOOR
        else:
            if (x + y) % 3 or x == 1 or y == 1 or x == MAP_WIDTH - 2 or y == MAP_HEIGHT - 2:
                map[y * MAP_WIDTH + x] = TILE_FLOOR
            else:
                map[y * MAP_WIDTH + x] = TILE_CHEST

# Robots start in the corners
robots = [
    { "id": 1, "x": 1, "y": 1, "directions": [], "connected": False },
    { "id": 2, "x": MAP_WIDTH - 2, "y": 1, "directions": [], "connected": False },
    { "id": 3, "x": 1, "y": MAP_HEIGHT - 2, "directions": [], "connected": False },
    { "id": 4, "x": MAP_WIDTH - 2, "y": MAP_HEIGHT - 2, "directions": [], "connected": False }
]

# Simple log function
def log(line):
    print("[ROBOT " + str(ROBOT_ID) + "] " + line)

# Websocket server connection
async def websocketConnection():
    log("Connecting with the websockets server at ws://127.0.0.1:" + str(WEBSOCKETS_PORT) + "...")
    try:
        async with websockets.connect("ws://127.0.0.1:" + str(WEBSOCKETS_PORT)) as websocket:
            # Send connect message
            robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
            await websocket.send(json.dumps({
                "type": "robot_connect",
                "data": {
                    "robot_id": ROBOT_ID,
                    "robot_x": robot["x"],
                    "robot_y": robot["y"],
                    "directions": []
                }
            }))
            robot["connected"] = True
            log("Robot " + str(ROBOT_ID) + " connected")

            # Message receive loop
            async for data in websocket:
                log("Server message: " + data)
                message = json.loads(data)

                # Connect message
                if message["type"] == "robot_connect":
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    otherRobot["x"] = message["data"]["robot_x"]
                    otherRobot["y"] = message["data"]["robot_y"]
                    otherRobot["directions"].clear()
                    for direction in message["data"]["directions"]:
                        otherRobot["directions"].append({
                            "id": direction["id"],
                            "x": direction["x"],
                            "y": direction["y"]
                        })
                    otherRobot["connected"] = True
                    log("Robot " + str(otherRobot["id"]) + " is connected")

                # Disconnect message
                if message["type"] == "robot_disconnect":
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    otherRobot["connected"] = False
                    log("Robot " + str(otherRobot["id"]) + " is disconnected")

                # World info message
                if message["type"] == "world_info":
                    for i in range(MAP_HEIGHT * MAP_WIDTH):
                        if map[i] == TILE_UNKOWN and message["data"]["map"][i] != TILE_UNKOWN:
                            map[i] = message["data"]["map"][i]

                # New Direction message
                if message["type"] == "new_direction":
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    otherRobot["directions"].append({
                        "id": message["data"]["direction"]["id"],
                        "x": message["data"]["direction"]["x"],
                        "y": message["data"]["direction"]["y"]
                    })
                    log("New direction for Robot " + str(otherRobot["id"]))

                # Cancel direction message
                if message["type"] == "cancel_direction":
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    for i, direction in enumerate(otherRobot["directions"]):
                        if direction["id"] == message["data"]["direction"]["id"]:
                            del otherRobot["directions"][i]
                            break
                    log("Cancel direction for robot " + str(otherRobot["id"]))

                # Tick message
                if message["type"] == "robot_tick":
                    if len(robot["directions"]) > 0:
                        log("Tick")

                        # TODO

                        # Calculate fastest path to robot["directions"][0]

                        # Do step in the right direction

                        # Read sensors and write back to map

                        # Send tick done message
                        await websocket.send(json.dumps({
                            "type": "robot_tick_done",
                            "data": {
                                "robot_id": ROBOT_ID,
                                "robot_x": robot["x"],
                                "robot_y": robot["y"],
                                "map": [
                                    { "x": robot["x"] - 1, "y": robot["y"], "type": map[robot["y"] * MAP_WIDTH + (robot["x"] - 1)] },
                                    { "x": robot["x"] + 1, "y": robot["y"], "type": map[robot["y"] * MAP_WIDTH + (robot["x"] + 1)] },
                                    { "x": robot["x"], "y": robot["y"] - 1, "type": map[(robot["y"] - 1) * MAP_WIDTH + robot["x"]] },
                                    { "x": robot["x"], "y": robot["y"] + 1, "type": map[(robot["y"] + 1) * MAP_WIDTH + robot["x"]] }
                                ]
                            }
                        }))

                        log("Tick done")

                # Tick done message
                if message["type"] == "robot_tick_done":
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    otherRobot["x"] = message["data"]["robot_x"]
                    otherRobot["y"] = message["data"]["robot_y"]

                    for mapUpdate in message["data"]["map"]:
                        map[mapUpdate["y"] * MAP_WIDTH + mapUpdate["x"]] = mapUpdate["type"]

                    log("Tick done from Robot " + otherRobot["id"])
    except:
        log("Can't connect to the websockets server")
        exit(1)

asyncio.run(websocketConnection())
