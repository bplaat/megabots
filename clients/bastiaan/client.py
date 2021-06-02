#!/usr/bin/env python

# Bastiaan's MegaBot client which can be all the robots via first argument
# This is also the reference client for the MegaBot protocol

import asyncio
import json
import random
import sys
import websockets

# Constants
DEBUG = False

ROBOT_ID = len(sys.argv) >= 2 and int(sys.argv[1]) or 1

WEBSOCKETS_URL = "ws://127.0.0.1:8080/"

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

# Map data is unkown until world info message from server
mapWidth = None
mapHeight = None
mapData = None

# Get all the neigbors of a point
def getTileNeighbors(point):
    neighbors = []
    if point["x"] > 0:
        neighbors.append({ "x": point["x"] - 1, "y": point["y"] })
    if point["y"] > 0:
        neighbors.append({ "x": point["x"], "y": point["y"] - 1 })
    if point["x"] < mapWidth - 1:
        neighbors.append({ "x": point["x"] + 1, "y": point["y"] })
    if point["y"] < mapHeight - 1:
        neighbors.append({ "x": point["x"], "y": point["y"] + 1 })
    return neighbors

# Simple inefficent Breadth First Search Algorithm for more info:
# https://www.redblobgames.com/pathfinding/a-star/introduction.html
def findPath(begin, end, withOtherRobots):
    frontier = [ { "x": begin["x"], "y": begin["y"] } ]
    cameFrom =  [[None] * mapWidth for i in range(mapHeight)]

    # Traverse complete map to search for end point
    while len(frontier) > 0:
        current = frontier[0]
        del frontier[0]

        # When end point is found stop searching
        if current["x"] == end["x"] and current["y"] == end["y"]:
            break

        neighbors = getTileNeighbors(current)
        random.shuffle(neighbors)
        for neighbor in neighbors:
            # Ignore other robot tiles
            if withOtherRobots:
                colliding = False
                for robot in robots:
                    if robot["connected"] and robot["x"] == neighbor["x"] and robot["y"] == neighbor["y"]:
                        colliding = True
                        break
                if colliding:
                    continue

            # Ignore chest tiles
            tileType = mapData[neighbor["y"]][neighbor["x"]]
            if not (tileType == TILE_FLOOR or tileType == TILE_UNKOWN):
                continue

            # Add tile to came from point map
            if cameFrom[neighbor["y"]][neighbor["x"]] == None:
                frontier.append(neighbor)
                cameFrom[neighbor["y"]][neighbor["x"]] = current

    # Reverse from end to find the shortest path to begin
    current = end
    path = []
    while True:
        # Path is imposible
        if current == None:
            return None

        # We are at the begin path complete
        if current["x"] == begin["x"] and current["y"] == begin["y"]:
            break

        path.append(current)
        current = cameFrom[current["y"]][current["x"]]
    path.reverse()
    return path

# Robots
robots = [
    { "id": 1, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 2, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 3, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 4, "x": None, "y": None, "directions": [], "connected": False }
]

# Simple log function
def log(line):
    if DEBUG:
        print("[ROBOT " + str(ROBOT_ID) + "] " + line)

# Websocket server connection
async def websocketConnection():
    global mapWidth, mapHeight, mapData

    robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
    tickCounter = 0

    log("Connecting with the websockets server at " + WEBSOCKETS_URL + "...")
    async with websockets.connect(WEBSOCKETS_URL) as websocket:
        async def sendMessage(type, data = {}):
            await websocket.send(json.dumps({
                "type": type,
                "data": data
            }, separators=(",", ":")))

        # Send robot connect message
        await sendMessage("robot_connect", { "robot_id": robot["id"] })

        async for data in websocket:
            log("Server message: " + data)
            message = json.loads(data)

            # World info message
            if message["type"] == "world_info":
                mapWidth = message["data"]["map"]["width"]
                mapHeight = message["data"]["map"]["height"]

                # Create map data
                mapData = [[TILE_UNKOWN] * mapWidth for i in range(mapHeight)]
                mapData[0][0] = TILE_FLOOR
                mapData[0][mapWidth - 1] = TILE_FLOOR
                mapData[mapHeight - 1][0] = TILE_FLOOR
                mapData[mapHeight - 1][mapWidth - 1] = TILE_FLOOR

                # Patch map data with given map
                for y in range(mapHeight):
                    for x in range(mapWidth):
                        if mapData[y][x] == TILE_UNKOWN and message["data"]["map"]["data"][y][x] != TILE_UNKOWN:
                            mapData[y][x] = message["data"]["map"]["data"][y][x]

            # Robot connect message
            if message["type"] == "robot_connect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["x"] = message["data"]["robot"]["x"]
                otherRobot["y"] = message["data"]["robot"]["y"]
                otherRobot["directions"] = []
                for direction in message["data"]["robot"]["directions"]:
                    otherRobot["directions"].append({
                        "id": direction["id"],
                        "x": direction["x"],
                        "y": direction["y"]
                    })
                otherRobot["connected"] = True
                log("Robot " + str(otherRobot["id"]) + " is connected")

            # Robot disconnect message
            if message["type"] == "robot_disconnect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["connected"] = False
                log("Robot " + str(otherRobot["id"]) + " is disconnected")

            # New direction message
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
                otherRobot["directions"] = [direction for direction in otherRobot["directions"] if direction["id"] != message["data"]["direction_id"]]
                log("Cancel direction for robot " + str(otherRobot["id"]))

            # Read sensors done message
            if message["type"] == "read_sensors_done":
                # Patch map data with given sensor data
                mapUpdates = []

                if robot["y"] > 0:
                    upType = message["data"]["sensors"]["up"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"] - 1][robot["x"]] = upType
                    mapUpdates.append({ "x": robot["x"], "y": robot["y"] - 1, "type": upType })

                if robot["x"] > 0:
                    leftType = message["data"]["sensors"]["left"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"]][robot["x"] - 1] = leftType
                    mapUpdates.append({ "x": robot["x"] - 1, "y": robot["y"], "type": leftType })

                if robot["x"] < mapWidth - 1:
                    rightType = message["data"]["sensors"]["right"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"]][robot["x"] + 1] = rightType
                    mapUpdates.append({ "x": robot["x"] + 1, "y": robot["y"], "type": rightType })

                if robot["y"] < mapHeight - 1:
                    downType = message["data"]["sensors"]["down"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"] + 1][robot["x"]] = downType
                    mapUpdates.append({ "x": robot["x"], "y": robot["y"] + 1, "type": downType })

                # Send tick done message
                log("Tick done")
                tickCounter += 1
                await sendMessage("robot_tick_done", {
                    "robot_id": robot["id"],
                    "robot": {
                        "x": robot["x"],
                        "y": robot["y"]
                    },
                    "map": mapUpdates
                })

            # Robot tick message
            if message["type"] == "robot_tick":
                # Ignore robot tick messages for other robots
                if message["data"]["robot_id"] != robot["id"]:
                    continue

                # When it is the first tick read only sensors
                if tickCounter == 0:
                    log("First tick read only sensors")
                    await sendMessage("read_sensors", { "robot_id": robot["id"] })
                    continue

                # Do nothing because no directions
                if len(robot["directions"]) == 0:
                    log("Tick done but no directions")
                    tickCounter += 1
                    await sendMessage("robot_tick_done", { "robot_id": robot["id"] })
                    continue

                # Check if we are not already at destination
                destination = { "x": robot["directions"][0]["x"], "y": robot["directions"][0]["y"] }
                if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                    # Cancel direction because complete
                    await sendMessage("cancel_direction", {
                        "robot_id": robot["id"],
                        "direction_id": robot["directions"][0]["id"]
                    })

                    # Do nothing because direction complete
                    log("Tick done but no directions")
                    tickCounter += 1
                    await sendMessage("robot_tick_done", { "robot_id": robot["id"] })
                    continue

                # Find path to destination
                start = { "x": robot["x"], "y": robot["y"] }
                path = findPath(start, destination, True)

                # If implosible check again without other robots to check if posible
                if path == None:
                    path = findPath(start, destination, False)
                    if path == None:
                        # Cancel direction because path imposible
                        await sendMessage("cancel_direction", {
                            "robot_id": robot["id"],
                            "direction_id": robot["directions"][0]["id"]
                        })

                        log("Tick done but direction canceled because impossible")
                        tickCounter += 1
                        await sendMessage("robot_tick_done", { "robot_id": robot["id"] })
                    else:
                        # Don't move wait until other robots are moved on
                        log("Tick done waiting for robot to move away")
                        tickCounter += 1
                        await sendMessage("robot_tick_done", { "robot_id": robot["id"] })
                else:
                    # Move robot one step
                    robot["x"] = path[0]["x"]
                    robot["y"] = path[0]["y"]

                    # When we are at the destination delete direction
                    if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                        # Cancel direction because complete
                        await sendMessage("cancel_direction", {
                            "robot_id": robot["id"],
                            "direction_id": robot["directions"][0]["id"]
                        })

                    # Read sensors of new position
                    await sendMessage("read_sensors", {
                        "robot_id": robot["id"],
                        "robot": {
                            "x": robot["x"],
                            "y": robot["y"]
                        }
                    })

            # Robot tick done message
            if message["type"] == "robot_tick_done":
                if robot["id"] != message["data"]["robot_id"]:
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    if "robot" in message["data"]:
                        otherRobot["x"] = message["data"]["robot"]["x"]
                        otherRobot["y"] = message["data"]["robot"]["y"]

                    if "map" in message["data"]:
                        for mapUpdate in message["data"]["map"]:
                            if mapData[mapUpdate["y"]][mapUpdate["x"]] == TILE_UNKOWN and mapUpdate["type"] != TILE_UNKOWN:
                                mapData[mapUpdate["y"]][mapUpdate["x"]] = mapUpdate["type"]

                    log("Tick done from Robot " + str(otherRobot["id"]))

asyncio.run(websocketConnection())
