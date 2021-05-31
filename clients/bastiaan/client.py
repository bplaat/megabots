#!/usr/bin/env python

import asyncio
import json
import os
import random
import sys
import websockets
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/..')
import events

# Constants
DEBUG = False

WEBSOCKETS_PORT = 8080

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
robotId = None
robots = [
    { "id": 1, "x": 0, "y": 0, "lift": 200, "directions": [], "connected": False },
    { "id": 2, "x": mapWidth - 1, "y": 0, "lift": 300, "directions": [], "connected": False },
    { "id": 3, "x": 0, "y": mapHeight - 1, "lift": 500, "directions": [], "connected": False },
    { "id": 4, "x": mapWidth - 1, "y": mapHeight - 1, "lift": 250, "directions": [], "connected": False }
]

# Simple log function
def log(line):
    if DEBUG:
        print("[ROBOT " + str(robotId) + "] " + line)

# Websocket server connection
async def websocketConnection():
    log("Connecting with the websockets server at ws://127.0.0.1:" + str(WEBSOCKETS_PORT) + "...")

    async with websockets.connect("ws://127.0.0.1:" + str(WEBSOCKETS_PORT)) as websocket:
        # Send connect message
        robot = next((robot for robot in robots if robot["id"] == robotId), None)
        await websocket.send(json.dumps({
            "type": "robot_connect",
            "data": {
                "robot_id": robotId,
                "robot_x": robot["x"],
                "robot_y": robot["y"],
                "robot_lift": robot["lift"],
                "directions": robot["directions"]
            }
        }, separators=(",", ":")))
        robot["connected"] = True
        log("Robot " + str(robotId) + " connected")

        # Send move message with current robot position
        events.send("move", { "robot_x": robot["x"], "robot_y": robot["y"] })

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
                    # Read sensors from controller and write back to map
                    mapUpdates = []
                    def sensorsResponseCallback(data):
                        for mapUpdate in data["map_updates"]:
                            position = mapUpdate["y"] * mapWidth + mapUpdate["x"]
                            if visibleMapData[position] == TILE_UNKOWN and mapUpdate["type"] != TILE_UNKOWN:
                                visibleMapData[position] = mapUpdate["type"]
                            mapUpdates.append({ "x": mapUpdate["x"], "y": mapUpdate["y"], "type": mapUpdate["type"] })
                    events.once("sensors_response", sensorsResponseCallback)
                    events.send("sensors")

                    # Check if we are not already at destination
                    destination = { "x": robot["directions"][0]["x"], "y": robot["directions"][0]["y"] }
                    if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                        # Cancel direction because complete
                        await websocket.send(json.dumps({
                            "type": "cancel_direction",
                            "data": {
                                "robot_id": robotId,
                                "direction": {
                                    "id": robot["directions"][0]["id"]
                                }
                            }
                        }, separators=(",", ":")))
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
                                        "robot_id": robotId,
                                        "direction": {
                                            "id": robot["directions"][0]["id"]
                                        }
                                    }
                                }, separators=(",", ":")))
                            else:
                                # Don't move wait until other robots are moved on
                                pass
                        else:
                            robot["x"] = path[0]["x"]
                            robot["y"] = path[0]["y"]

                            # Send move message to controller
                            events.send("move", { "robot_x": robot["x"], "robot_y": robot["y"] })

                            # Read sensors again of new position
                            events.once("sensors_response", sensorsResponseCallback)
                            events.send("sensors")

                            # When we are at the destination delete direction
                            if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                                # Cancel direction because complete
                                await websocket.send(json.dumps({
                                    "type": "cancel_direction",
                                    "data": {
                                        "robot_id": robotId,
                                        "direction": {
                                            "id": robot["directions"][0]["id"]
                                        }
                                    }
                                }, separators=(",", ":")))

                    # Send tick done message
                    await websocket.send(json.dumps({
                        "type": "robot_tick_done",
                        "data": {
                            "robot_id": robotId,
                            "robot_x": robot["x"],
                            "robot_y": robot["y"],
                            "map": mapUpdates
                        }
                    }, separators=(",", ":")))
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

# Controller sends start message to init and start robot connection
def startCallback(data):
    global robotId
    robotId = data["robot_id"]
    asyncio.run(websocketConnection())
events.once("start", startCallback)

# When started directly the robot emultes his own controller
def robotController():
    robotId = len(sys.argv) >= 2 and int(sys.argv[1]) or 1
    robotX = None
    robotY = None

    # Listen to sensors callbacks
    def sensorsCallback(data):
        global robotX, robotY
        mapUpdates = []
        if robotX > 0:
            mapUpdates.append({ "x": robotX - 1, "y": robotY, "type": mapData[robotY * mapWidth + (robotX - 1)] })
        if robotX < mapWidth - 1:
            mapUpdates.append({ "x": robotX + 1, "y": robotY, "type": mapData[robotY * mapWidth + (robotX + 1)] })
        if robotY > 0:
            mapUpdates.append({ "x": robotX, "y": robotY - 1, "type": mapData[(robotY - 1) * mapWidth + robotX] })
        if robotY < mapHeight - 1:
            mapUpdates.append({ "x": robotX, "y": robotY + 1, "type": mapData[(robotY + 1) * mapWidth + robotX] })
        events.send("sensors_response", { "map_updates": mapUpdates })
    events.on("sensors", sensorsCallback)

    # Listen to move events to update local robot position
    def moveCallback(data):
        global robotX, robotY
        robotX = data["robot_x"]
        robotY = data["robot_y"]
    events.on("move", moveCallback)

    # Send start message last to start connection (no return because async websocket connection!)
    events.send("start", { "robot_id": robotId })

if __name__ == "__main__":
    robotController()
