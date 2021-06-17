#!/usr/bin/env python

# Rowdey's MegaBot client

import asyncio
import json
import websockets
import collections

# Constants
DEBUG = False

ROBOT_ID = 4

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
    if point[0] > 0:
        neighbors.append((point[0] - 1,point[1]))
    if point[1] > 0:
        neighbors.append((point[0], point[1] - 1))
    if point[0] < mapWidth - 1:
        neighbors.append((point[0] + 1, point[1]))
    if point[1] < mapHeight - 1:
        neighbors.append((point[0], point[1] + 1))
    return neighbors


# Queue class for path finding
class Queue:
    def __init__(self):
        self.elements = collections.deque()

    def empty(self) -> bool:
        return not self.elements

    def put(self, x):
        self.elements.append(x)

    def get(self):
        return self.elements.popleft()


# Path finding algorithm based on Breadth-first search algorithm
def findPath(begin, finish, withOtherRobots):

    # Make tuples of coords
    start = (begin["x"], begin["y"])
    end = (finish["x"], finish["y"])
    frontier = Queue()
    frontier.put(start)
    came_from= {}

    while not frontier.empty():
        current = frontier.get()

        # If finish point is found, stop searching for path
        if current == end:
            break

        # Check if tile is traversable
        tileTypeCurrent = mapData[current[1]][current[0]]
        if(tileTypeCurrent == TILE_FLOOR or tileTypeCurrent == TILE_UNKOWN):

            for next in getTileNeighbors(current):

                # Check if other robots are blocking the path
                if withOtherRobots:
                    colliding = False
                    for robot in robots:
                        if robot["connected"] and robot["x"] == next[0] and robot["y"] == next[1]:
                            came_from[next] = None
                            colliding = True
                            break
                    if colliding:
                        continue

                # Check if tile is traversable
                tileType = mapData[next[1]][next[0]]
                if  (tileType == TILE_FLOOR or tileType == TILE_UNKOWN):

                    if next not in came_from:
                        frontier.put(next)
                        came_from[next] = current


    current = end
    # Check if finish points is reachable
    tileTypeCurrent = mapData[current[1]][current[0]]
    if(tileTypeCurrent == TILE_CHEST):
        return None

    path = []
    while current != start:
        if current in came_from.keys() :
            path.append(current)
            current = came_from[current]
        else:
            return None
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

                # If impossible check again without other robots to check if possible
                if path == None:
                    path = findPath(start, destination, False)
                    if path == None:
                        # Cancel direction because path impossible
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
                    robot["x"] = path[0][0]
                    robot["y"] = path[0][1]

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
