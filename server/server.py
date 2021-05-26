#!/usr/bin/env python

import asyncio
import json
import websockets

# Constants
DEBUG = False

WEBSOCKETS_PORT = 8080

TICK_MANUAL = 0
TICK_AUTO = 1

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
TILE_WALL = 3

# Simple asyncio timer class
class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()

# Load map from file
mapFile = open("map.json", "r")
mapFileData = json.loads(mapFile.read())
mapWidth = mapFileData["width"]
mapHeight = mapFileData["height"]
mapFile.close()

# Server tick information
tickType = TICK_MANUAL
tickSpeed = 200

# Init square map with robots in corners and all around wall rest unkown
mapData = [TILE_UNKOWN] * (mapHeight * mapWidth)
for y in range(mapHeight):
    for x in range(mapWidth):
        if x == 0 or y == 0 or x == mapWidth - 1 or y == mapHeight - 1:
            mapData[y * mapWidth + x] = TILE_WALL
        if (
            (x == 1 and y == 1) or
            (x == mapWidth - 2 and y == 1) or
            (x == 1 and y == mapHeight - 2) or
            (x == mapWidth - 2 and y == mapHeight - 2)
        ):
            mapData[y * mapWidth + x] = TILE_FLOOR

# Robots start in the corners
robots = [
    { "id": 1, "x": None, "y": None, "lift": None, "directions": [], "websocket": None },
    { "id": 2, "x": None, "y": None, "lift": None, "directions": [], "websocket": None },
    { "id": 3, "x": None, "y": None, "lift": None, "directions": [], "websocket": None },
    { "id": 4, "x": None, "y": None, "lift": None, "directions": [], "websocket": None }
]

# Website connections data
websites = []

# Simple log function
def log(line):
    if DEBUG:
        print("[SERVER] " + line)

# Timer callback
currentRobotIndex = None
async def tick():
    global currentRobotIndex

    for website in websites:
        await website["websocket"].send(json.dumps({
            "type": "website_tick",
            "data": {}
        }, separators=(',', ':')))

    # Tick first robot in the robot_tick_done will the next robot be ticked
    currentRobotIndex = 0
    log("Tick for Robot " + str(robots[currentRobotIndex]["id"]))
    await robots[currentRobotIndex]["websocket"].send(json.dumps({
        "type": "robot_tick",
        "data": {}
    }, separators=(',', ':')))
    currentRobotIndex += 1

async def timerCallback():
    await tick()
    if tickType == TICK_AUTO:
        Timer(tickSpeed / 1000, timerCallback)

# Websocket server
async def websocketConnection(websocket, path):
    global tickType, tickSpeed, currentRobotIndex

    async for data in websocket:
        log("Client message: " + data)
        message = json.loads(data)

        # Connect message
        if message["type"] == "robot_connect":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["x"] = message["data"]["robot_x"]
            robot["y"] = message["data"]["robot_y"]
            robot["lift"] = message["data"]["robot_lift"]
            robot["directions"].clear()
            for direction in message["data"]["directions"]:
                robot["directions"].append({
                    "id": direction["id"],
                    "x": direction["x"],
                    "y": direction["y"]
                })
            robot["websocket"] = websocket
            log("Robot " + str(robot["id"]) + " is connected")

            # Send world info message
            await websocket.send(json.dumps({
                "type": "world_info",
                "data": {
                    "tick_type": tickType,
                    "tick_speed": tickSpeed,
                    "map": {
                        "width": mapWidth,
                        "height": mapHeight,
                        "data": mapData
                    }
                }
            }, separators=(',', ':')))

            # Send other robot connected messages
            for otherRobot in robots:
                if otherRobot["websocket"] != None and otherRobot["id"] != robot["id"]:
                    # Send robot connect message of this other robot
                    await websocket.send(json.dumps({
                        "type": "robot_connect",
                        "data": {
                            "robot_id": otherRobot["id"],
                            "robot_x": otherRobot["x"],
                            "robot_y": otherRobot["y"],
                            "robot_lift": otherRobot["lift"],
                            "directions": otherRobot["directions"]
                        }
                    }, separators=(',', ':')))

                    # Send other robot connect message of this robot
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "robot_connect",
                        "data": {
                            "robot_id": robot["id"],
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "robot_lift": robot["lift"],
                            "directions": robot["directions"]
                        }
                    }, separators=(',', ':')))

            # Send other websites connected messages
            for website in websites:
                # Send robot connect message of this website
                await websocket.send(json.dumps({
                    "type": "website_connect",
                    "data": {
                        "website_id": website["id"]
                    }
                }, separators=(',', ':')))

                # Send this website connect message of this robot
                await website["websocket"].send(json.dumps({
                    "type": "robot_connect",
                    "data": {
                        "robot_id": robot["id"],
                        "robot_x": robot["x"],
                        "robot_y": robot["y"],
                        "robot_lift": robot["lift"],
                        "directions": robot["directions"]
                    }
                }, separators=(',', ':')))

        # Website connect message
        if message["type"] == "website_connect":
            website = {
                "id": message["data"]["website_id"],
                "websocket": websocket
            }
            websites.append(website)
            log("Website " + str(website["id"]) + " is connected")

            # Send world info message
            await websocket.send(json.dumps({
                "type": "world_info",
                "data": {
                    "tick_type": tickType,
                    "tick_speed": tickSpeed,
                    "map": {
                        "width": mapWidth,
                        "height": mapHeight,
                        "data": mapData
                    }
                }
            }, separators=(',', ':')))

            # Send robot connected messages
            for robot in robots:
                if robot["websocket"] != None:
                    # Send website connect message of this robot
                    await websocket.send(json.dumps({
                        "type": "robot_connect",
                        "data": {
                            "robot_id": robot["id"],
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "robot_lift": robot["lift"],
                            "directions": robot["directions"]
                        }
                    }, separators=(',', ':')))

                    # Send robot connect message of this website
                    await robot["websocket"].send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": website["id"]
                        }
                    }, separators=(',', ':')))

            # Send other websites connected messages
            for otherWebsite in websites:
                if otherWebsite["id"] != website["id"]:
                    # Send website connect message of this website
                    await websocket.send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": otherWebsite["id"]
                        }
                    }, separators=(',', ':')))

                    # Send this website connect message of this other website
                    await otherWebsite["websocket"].send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": website["id"]
                        }
                    }, separators=(',', ':')))

        # Update world info message
        if message["type"] == "update_world_info":
            messageData = {}

            if "tick_speed" in message["data"]:
                tickSpeed = message["data"]["tick_speed"]
                messageData["tick_speed"] = tickSpeed

            if "tick_type" in message["data"]:
                oldTickType = tickType
                tickType = message["data"]["tick_type"]
                messageData["tick_type"] = tickType

                if oldTickType == TICK_MANUAL and tickType == TICK_AUTO:
                    Timer(tickSpeed / 1000, timerCallback)

            for robot in robots:
                if robot["websocket"] != None:
                    await robot["websocket"].send(json.dumps({
                        "type": "update_world_info",
                        "data": messageData
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "update_world_info",
                    "data": messageData
                }, separators=(',', ':')))

        # World tick message
        if message["type"] == "world_tick":
            await tick()

        # New direction message
        if message["type"] == "new_direction":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["directions"].append({
                "id": message["data"]["direction"]["id"],
                "x": message["data"]["direction"]["x"],
                "y": message["data"]["direction"]["y"]
            })
            log("New direction for Robot " + str(robot["id"]))

            for otherRobot in robots:
                if otherRobot["websocket"] != None:
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "new_direction",
                        "data": {
                            "robot_id": robot["id"],
                            "direction": {
                                "id": message["data"]["direction"]["id"],
                                "x": message["data"]["direction"]["x"],
                                "y": message["data"]["direction"]["y"]
                            }
                        }
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "new_direction",
                    "data": {
                        "robot_id": robot["id"],
                        "direction": {
                            "id": message["data"]["direction"]["id"],
                            "x": message["data"]["direction"]["x"],
                            "y": message["data"]["direction"]["y"]
                        }
                    }
                }, separators=(',', ':')))

        # Cancel direction message
        if message["type"] == "cancel_direction":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            for i, direction in enumerate(robot["directions"]):
                if direction["id"] == message["data"]["direction"]["id"]:
                    del robot["directions"][i]
                    break
            log("Cancel direction for Robot " + str(robot["id"]))

            for otherRobot in robots:
                if otherRobot["websocket"] != None:
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "cancel_direction",
                        "data": {
                            "robot_id": robot["id"],
                            "direction": {
                                "id": message["data"]["direction"]["id"]
                            }
                        }
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "cancel_direction",
                    "data": {
                        "robot_id": robot["id"],
                        "direction": {
                            "id": message["data"]["direction"]["id"]
                        }
                    }
                }, separators=(',', ':')))

        # Tick done message
        if message["type"] == "robot_tick_done":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["x"] = message["data"]["robot_x"]
            robot["y"] = message["data"]["robot_y"]

            mapUpdates = []
            for mapUpdate in message["data"]["map"]:
                position = mapUpdate["y"] * mapWidth + mapUpdate["x"]
                if mapData[position] == TILE_UNKOWN and mapUpdate["type"] != TILE_UNKOWN:
                    mapData[position] = mapUpdate["type"]

                    mapUpdates.append({
                        "x": mapUpdate["x"],
                        "y": mapUpdate["y"],
                        "type": mapUpdate["type"]
                    })

            log("Tick done from Robot " + str(robot["id"]))

            for otherRobot in robots:
                if otherRobot["websocket"] != None and otherRobot["id"] != robot["id"]:
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "robot_tick_done",
                        "data": {
                            "robot_id": robot["id"],
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "map": mapUpdates
                        }
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "robot_tick_done",
                    "data": {
                        "robot_id": robot["id"],
                        "robot_x": robot["x"],
                        "robot_y": robot["y"],
                        "map": mapUpdates
                    }
                }, separators=(',', ':')))

            if currentRobotIndex < len(robots):
                log("Tick for Robot " + str(robots[currentRobotIndex]["id"]))
                await robots[currentRobotIndex]["websocket"].send(json.dumps({
                    "type": "robot_tick",
                    "data": {}
                }, separators=(',', ':')))
                currentRobotIndex += 1

    # Disconnect message for robots
    for robot in robots:
        if robot["websocket"] == websocket:
            log("Robot " + str(robot["id"]) + " is disconnected")
            robot["websocket"] = None

            for otherRobot in robots:
                if otherRobot["websocket"] != None:
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "robot_disconnect",
                        "data": {
                            "robot_id": robot["id"]
                        }
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "robot_disconnect",
                    "data": {
                        "robot_id": robot["id"]
                    }
                }, separators=(',', ':')))

            break

    # Disconnect message for websites
    for website in websites:
        if website["websocket"] == websocket:
            website_id = website["id"]
            log("Website " + str(website_id) + " is disconnected")

            for i, website in enumerate(websites):
                if website["id"] == website_id:
                    del websites[i]
                    break

            for robot in robots:
                if robot["websocket"] != None:
                    await robot["websocket"].send(json.dumps({
                        "type": "website_disconnect",
                        "data": {
                            "website_id": website_id
                        }
                    }, separators=(',', ':')))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "website_disconnect",
                    "data": {
                        "website_id": website_id
                    }
                }, separators=(',', ':')))

            break

# Create websockets server
async def websocketsServer():
    log("Websockets server is listening at ws://127.0.0.1:" + str(WEBSOCKETS_PORT))
    async with websockets.serve(websocketConnection, "127.0.0.1", WEBSOCKETS_PORT):
        await asyncio.Future()

asyncio.run(websocketsServer())
