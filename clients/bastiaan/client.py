#!/usr/bin/env python

import asyncio
import json
import random
import sys
import websockets

# Constants
DEBUG = False

WEBSOCKETS_PORT = 8080

ROBOT_ID = len(sys.argv) >= 2 and int(sys.argv[1]) or 1

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

# Load map from file
mapFile = open("map.json", "r")
mapFileData = json.loads(mapFile.read())
mapWidth = mapFileData["width"]
mapHeight = mapFileData["height"]
mapData = mapFileData["data"]
mapFile.close()

# Init square map with robots in corners and rest unkown
visibleMapData = [TILE_UNKOWN] * (mapHeight * mapWidth)
visibleMapData[0 * mapWidth + 0] = TILE_FLOOR
visibleMapData[0 * mapWidth + (mapWidth - 1)] = TILE_FLOOR
visibleMapData[(mapHeight - 1) * mapWidth + 0] = TILE_FLOOR
visibleMapData[(mapHeight - 1) * mapWidth + (mapWidth - 1)] = TILE_FLOOR

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
    cameFrom = [None] * (mapHeight * mapWidth)

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
                    if robot["x"] == neighbor["x"] and robot["y"] == neighbor["y"]:
                        colliding = True
                        break
                if colliding:
                    continue

            # Ignore chest tiles
            tileType = visibleMapData[neighbor["y"] * mapWidth + neighbor["x"]]
            if not (tileType == TILE_FLOOR or tileType == TILE_UNKOWN):
                continue

            # Add tile to came from point map
            if cameFrom[neighbor["y"] * mapWidth + neighbor["x"]] == None:
                frontier.append(neighbor)
                cameFrom[neighbor["y"] * mapWidth + neighbor["x"]] = current

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
        current = cameFrom[current["y"] * mapWidth + current["x"]]
    path.reverse()
    return path

# Robots start in the corners
robots = [
    { "id": 1, "x": 0, "y": 0, "lift": 200, "directions": [], "connected": False },
    { "id": 2, "x": mapWidth - 1, "y": 0, "lift": 300, "directions": [], "connected": False },
    { "id": 3, "x": 0, "y": mapHeight - 1, "lift": 500, "directions": [], "connected": False },
    { "id": 4, "x": mapWidth - 1, "y": mapHeight - 1, "lift": 250, "directions": [], "connected": False }
]

# Simple log function
def log(line):
    if DEBUG:
        print("[ROBOT " + str(ROBOT_ID) + "] " + line)

# Websocket server connection
async def websocketConnection():
    log("Connecting with the websockets server at ws://127.0.0.1:" + str(WEBSOCKETS_PORT) + "...")

    async with websockets.connect("ws://127.0.0.1:" + str(WEBSOCKETS_PORT)) as websocket:
        # Send connect message
        robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
        await websocket.send(json.dumps({
            "type": "robot_connect",
            "data": {
                "robot_id": ROBOT_ID,
                "robot_x": robot["x"],
                "robot_y": robot["y"],
                "robot_lift": robot["lift"],
                "directions": robot["directions"]
            }
        }, separators=(',', ':')))
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
                otherRobot["lift"] = message["data"]["robot_lift"]
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
                for i in range(mapHeight * mapWidth):
                    if visibleMapData[i] == TILE_UNKOWN and message["data"]["map"]["data"][i] != TILE_UNKOWN:
                        visibleMapData[i] = message["data"]["map"]["data"][i]

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
                    # Read sensors from real map and write back to map
                    mapUpdates = []
                    def readSensors():
                        if robot["x"] > 0:
                            visibleMapData[robot["y"] * mapWidth + (robot["x"] - 1)] = mapData[robot["y"] * mapWidth + (robot["x"] - 1)]
                            mapUpdates.append({ "x": robot["x"] - 1, "y": robot["y"], "type": visibleMapData[robot["y"] * mapWidth + (robot["x"] - 1)] })
                        if robot["x"] < mapWidth - 1:
                            visibleMapData[robot["y"] * mapWidth + (robot["x"] + 1)] = mapData[robot["y"] * mapWidth + (robot["x"] + 1)]
                            mapUpdates.append({ "x": robot["x"] + 1, "y": robot["y"], "type": visibleMapData[robot["y"] * mapWidth + (robot["x"] + 1)] })
                        if robot["y"] > 0:
                            visibleMapData[(robot["y"] - 1) * mapWidth + robot["x"]] = mapData[(robot["y"] - 1) * mapWidth + robot["x"]]
                            mapUpdates.append({ "x": robot["x"], "y": robot["y"] - 1, "type": visibleMapData[(robot["y"] - 1) * mapWidth + robot["x"]] })
                        if robot["y"] < mapHeight - 1:
                            visibleMapData[(robot["y"] + 1) * mapWidth + robot["x"]] = mapData[(robot["y"] + 1) * mapWidth + robot["x"]]
                            mapUpdates.append({ "x": robot["x"], "y": robot["y"] + 1, "type": visibleMapData[(robot["y"] + 1) * mapWidth + robot["x"]] })
                    readSensors()

                    # Check if we are not already at destination
                    destination = { "x": robot["directions"][0]["x"], "y": robot["directions"][0]["y"] }
                    if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                        # Cancel direction because complete
                        await websocket.send(json.dumps({
                            "type": "cancel_direction",
                            "data": {
                                "robot_id": ROBOT_ID,
                                "direction": {
                                    "id": robot["directions"][0]["id"]
                                }
                            }
                        }, separators=(',', ':')))
                    else:
                        # Find path to destination
                        start = { "x": robot["x"], "y": robot["y"] }
                        path = findPath(start, destination, True)

                        # If implosible check again without other robots to check if posible
                        if path == None:
                            path = findPath(start, destination, False)
                            if path == None:
                                # Cancel direction because path imposible
                                await websocket.send(json.dumps({
                                    "type": "cancel_direction",
                                    "data": {
                                        "robot_id": ROBOT_ID,
                                        "direction": {
                                            "id": robot["directions"][0]["id"]
                                        }
                                    }
                                }, separators=(',', ':')))
                            else:
                                # Don't move wait until other robots are moved on
                                pass
                        else:
                            robot["x"] = path[0]["x"]
                            robot["y"] = path[0]["y"]

                            # Read sensors again of new position
                            readSensors()

                            # When we are at the destination delete direction
                            if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                                # Cancel direction because complete
                                await websocket.send(json.dumps({
                                    "type": "cancel_direction",
                                    "data": {
                                        "robot_id": ROBOT_ID,
                                        "direction": {
                                            "id": robot["directions"][0]["id"]
                                        }
                                    }
                                }, separators=(',', ':')))

                    # Send tick done message
                    await websocket.send(json.dumps({
                        "type": "robot_tick_done",
                        "data": {
                            "robot_id": ROBOT_ID,
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "map": mapUpdates
                        }
                    }, separators=(',', ':')))
                    log("Tick done")
                else:
                    log("Tick ignored because no directions")

            # Tick done message
            if message["type"] == "robot_tick_done":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["x"] = message["data"]["robot_x"]
                otherRobot["y"] = message["data"]["robot_y"]

                for mapUpdate in message["data"]["map"]:
                    position = mapUpdate["y"] * mapWidth + mapUpdate["x"]
                    if visibleMapData[position] == TILE_UNKOWN and mapUpdate["type"] != TILE_UNKOWN:
                        visibleMapData[position] = mapUpdate["type"]

                log("Tick done from Robot " + str(otherRobot["id"]))

asyncio.run(websocketConnection())
