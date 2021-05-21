#!/usr/bin/env python

import asyncio
import websockets
import json

# Constants
WEBSOCKETS_PORT = 8080

TICK_AUTO = 0
TICK_MANUAL = 1

MAP_WIDTH = 16
MAP_HEIGHT = 16

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
TILE_WALL = 3

# Server tick information
tickType = TICK_MANUAL
tickSpeed = 500
currentRobotIndex = 0

# Init square map with robots in corners and all around wall rest unkown
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
            map[y * MAP_WIDTH + x] = TILE_FLOOR

# Robots start in the corners
robots = [
    { "id": 1, "x": None, "y": None, "directions": [], "websocket": None },
    { "id": 2, "x": None, "y": None, "directions": [], "websocket": None },
    { "id": 3, "x": None, "y": None, "directions": [], "websocket": None },
    { "id": 4, "x": None, "y": None, "directions": [], "websocket": None }
]

# Website connections data
websites = []

# Simple log function
def log(line):
    print("[SERVER] " + line)

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
                    "map": map
                }
            }))

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
                            "directions": otherRobot["directions"]
                        }
                    }))

                    # Send other robot connect message of this robot
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "robot_connect",
                        "data": {
                            "robot_id": robot["id"],
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "directions": robot["directions"]
                        }
                    }))

            # Send other websites connected messages
            for website in websites:
                # Send robot connect message of this website
                await websocket.send(json.dumps({
                    "type": "website_connect",
                    "data": {
                        "website_id": website["id"]
                    }
                }))

                # Send this website connect message of this robot
                await website["websocket"].send(json.dumps({
                    "type": "robot_connect",
                    "data": {
                        "robot_id": robot["id"],
                        "robot_x": robot["x"],
                        "robot_y": robot["y"],
                        "directions": robot["directions"]
                    }
                }))

        # Website connect message
        if message["type"] == "website_connect":
            website =  {
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
                    "map": map
                }
            }))

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
                            "directions": robot["directions"]
                        }
                    }))

                    # Send robot connect message of this website
                    await robot["websocket"].send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": website["id"]
                        }
                    }))

            # Send other websites connected messages
            for otherWebsite in websites:
                if otherWebsite["id"] != website["id"]:
                    # Send website connect message of this website
                    await websocket.send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": otherWebsite["id"]
                        }
                    }))

                    # Send this website connect message of this other website
                    await otherWebsite["websocket"].send(json.dumps({
                        "type": "website_connect",
                        "data": {
                            "website_id": website["id"]
                        }
                    }))

        # Update world info message
        if message["type"] == "update_world_info":
            messageData = {}

            if "tick_type" in message["data"]:
                tickType = message["data"]["tick_type"]
                messageData["tick_type"] = tickType

            if "tick_speed" in message["data"]:
                tickSpeed = message["data"]["tick_speed"]
                messageData["tick_speed"] = tickSpeed

            for robot in robots:
                if robot["websocket"] != None:
                    await robot["websocket"].send(json.dumps({
                        "type": "update_world_info",
                        "data": messageData
                    }))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "update_world_info",
                    "data": messageData
                }))

        # World tick message
        if message["type"] == "world_tick":
            while currentRobotIndex < len(robots):
                robot = robots[currentRobotIndex]
                log("Tick for Robot " + str(robot["id"]))

                await robot["websocket"].send(json.dumps({
                    "type": "robot_tick",
                    "data": {}
                }))

                currentRobotIndex += 1

            currentRobotIndex = 0

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
                    }))

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
                }))

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
                    }))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "cancel_direction",
                    "data": {
                        "robot_id": robot["id"],
                        "direction": {
                            "id": message["data"]["direction"]["id"]
                        }
                    }
                }))

        # Tick done message
        if message["type"] == "robot_tick_done":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["x"] = message["data"]["robot_x"]
            robot["y"] = message["data"]["robot_y"]

            mapUpdates = []
            for mapUpdate in message["data"]["map"]:
                map[mapUpdate["y"] * MAP_HEIGHT + mapUpdate["x"]] = mapUpdate["type"]
                mapUpdates.append({
                    "x": mapUpdate["x"],
                    "y": mapUpdate["y"],
                    "type": mapUpdate["type"]
                })

            log("Tick done from Robot " + str(robot["id"]))

            for otherRobot in robots:
                if otherRobot["websocket"] != None:
                    await otherRobot["websocket"].send(json.dumps({
                        "type": "robot_tick_done",
                        "data": {
                            "robot_id": robot["id"],
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "map": mapUpdates
                        }
                    }))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "robot_tick_done",
                    "data": {
                        "robot_id": robot["id"],
                        "robot_x": robot["x"],
                        "robot_y": robot["y"],
                        "map": mapUpdates
                    }
                }))

    # Disconnect message
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
                    }))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "robot_disconnect",
                    "data": {
                        "robot_id": robot["id"]
                    }
                }))

            break

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
                    }))

            for website in websites:
                await website["websocket"].send(json.dumps({
                    "type": "website_disconnect",
                    "data": {
                        "website_id": website_id
                    }
                }))

            break

async def websocketsServer():
    log("Websockets server is listening at ws://127.0.0.1:" + str(WEBSOCKETS_PORT))
    async with websockets.serve(websocketConnection, "127.0.0.1", WEBSOCKETS_PORT):
        await asyncio.Future()

asyncio.run(websocketsServer())
