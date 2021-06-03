#!/usr/bin/env python

import asyncio
import json
import random
import time
import websockets

# Constants
DEBUG = False

WEBSOCKETS_PORT = 8080

TICK_MANUAL = 0
TICK_AUTO = 1

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

# Simple asyncio timer class
class Timer:
    def __init__(self, timeout, callback, extra):
        self._timeout = timeout
        self._callback = callback
        self._extra = extra
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(self._extra)

    def cancel(self):
        self._task.cancel()

# Map data is unkown until supervisor connect message from supervisor
mapWidth = None
mapHeight = None
mapData = None

# Server tick information
tickType = TICK_MANUAL
tickSpeed = 200

# Robots
robots = [
    { "id": 1, "x": None, "y": None, "lift": 200, "color": { "red": 1, "green": 0, "blue": 0 },"directions": [], "websocket": None },
    { "id": 2, "x": None, "y": None, "lift": 300, "color": { "red": 0, "green": 1, "blue": 0 },"directions": [], "websocket": None },
    { "id": 3, "x": None, "y": None, "lift": 500, "color": { "red": 1, "green": 1, "blue": 0 },"directions": [], "websocket": None },
    { "id": 4, "x": None, "y": None, "lift": 250, "color": { "red": 0, "green": 0, "blue": 1 }, "directions": [], "websocket": None }
]

# Other connections data
others = []

# Simple log function
def log(line):
    if DEBUG:
        print("[SERVER] " + line)

# Websocket helper functions
async def sendMessage(item, type, data = {}):
    await item["websocket"].send(json.dumps({
        "type": type,
        "data": data
    }, separators=(",", ":")))

async def broadcastMessage(type, data = {}):
    for robot in robots:
        if robot["websocket"] != None:
            await sendMessage(robot, type, data)

    for other in others:
        await sendMessage(other, type, data)

async def sendWorldMessageTimerCallback(item):
    # Wait until Webots supervisor is connected and given map data
    if mapData == None:
        timer = Timer(250, sendWorldMessageTimerCallback, item)
    else:
        sendWorldMessage(item)

async def sendWorldMessage(item):
    # Wait until Webots supervisor is connected and given map data
    if mapData == None:
        timer = Timer(250, sendWorldMessageTimerCallback, item)
    else:
        programsData = []
        for program in programs:
            programsData.append({ "id": program["id"], "name": program["name"] })

        await sendMessage(item, "world_info", {
            "tick": {
                "type": tickType,
                "speed": tickSpeed
            },
            "active_program_id": activeProgram["id"],
            "programs": programsData,
            "map": {
                "width": mapWidth,
                "height": mapHeight,
                "data": mapData
            }
        })

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

# Discover program
async def discoverProgram():
    # Get list off all unkown tiles that are not arounded with chests
    unkownTiles = []
    unkownMap = [[False] * mapWidth for i in range(mapHeight)]
    for y in range(mapHeight):
        for x in range(mapWidth):
            if mapData[y][x] == TILE_UNKOWN and not (
                (x > 0 and mapData[y][x - 1] == TILE_CHEST) and
                (y > 0 and mapData[y - 1][x] == TILE_CHEST) and
                (x < mapWidth - 1 and mapData[y][x + 1] == TILE_CHEST) and
                (y < mapHeight - 1 and mapData[y + 1][x] == TILE_CHEST)
            ):
                unkownTiles.append({ "x": x, "y": y })
                unkownMap[y][x] = True
    if len(unkownTiles) == 0:
        return

    for robot in robots:
        if len(robot["directions"]) == 0 and len(unkownTiles) > 0:
            # A even simpeler version off the path finding
            # algorithm to search for finding the closesd unkown tile
            frontier = [ { "x": robot["x"], "y": robot["y"] } ]
            cameFrom =  [[None] * mapWidth for i in range(mapHeight)]

            while len(frontier) > 0:
                current = frontier[0]
                del frontier[0]

                if unkownMap[current["y"]][current["x"]]:
                    # Drive robot to closest unkown tile and broadcast new direction
                    direction = {
                        "id": round(time.time() * 1000),
                        "x": current["x"],
                        "y": current["y"]
                    }
                    robot["directions"].append(direction)
                    await broadcastMessage("new_direction", {
                        "robot_id": robot["id"],
                        "direction": direction
                    })

                    # Remove tile from list
                    unkownTiles = [unkownTile for unkownTile in unkownTiles if not (unkownTile["x"] == current["x"] and unkownTile["y"] == current["y"])]
                    unkownMap[current["y"]][current["x"]] = False
                    break

                neighbors = getTileNeighbors(current)
                random.shuffle(neighbors)
                for neighbor in neighbors:
                    tileType = mapData[neighbor["y"]][neighbor["x"]]
                    if not (tileType == TILE_FLOOR or tileType == TILE_UNKOWN):
                        continue

                    if cameFrom[neighbor["y"]][neighbor["x"]] == None:
                        frontier.append(neighbor)
                        cameFrom[neighbor["y"]][neighbor["x"]] = current


# Random directions program
async def randomDirectionsProgram():
    for robot in robots:
        if len(robot["directions"]) == 0:
            # Drive robot to a random floor tile
            x = None
            y = None
            while True:
                x = random.randint(0, mapWidth - 1)
                y = random.randint(0, mapHeight - 1)
                if mapData[y][x] != TILE_CHEST:
                    break

            # Broadcast new direction
            direction = {
                "id": round(time.time() * 1000),
                "x": x,
                "y": y
            }
            robot["directions"].append(direction)
            await broadcastMessage("new_direction", {
                "robot_id": robot["id"],
                "direction": direction
            })

# Programs
programs = [
    { "id": 1, "name": "None", "function": None },
    { "id": 2, "name": "Discover map", "function": discoverProgram },
    { "id": 3, "name": "Random directions", "function": randomDirectionsProgram }
]
activeProgram = next((program for program in programs if program["id"] == 2), None)

# Start a tick cycle
currentRobotIndex = None
async def tick():
    global currentRobotIndex

    # Run active program
    if activeProgram["function"] != None:
        await activeProgram["function"]()

    # Tick first robot in the robot_tick_done will the next robot be ticked
    currentRobotIndex = 0
    log("Tick for Robot " + str(robots[currentRobotIndex]["id"]))
    await broadcastMessage("robot_tick", { "robot_id": robots[currentRobotIndex]["id"] })
    currentRobotIndex += 1

# Ticker timer callback
async def timerCallback(extra):
    await tick()
    if tickType == TICK_AUTO:
        Timer(tickSpeed / 1000, timerCallback, None)

async def websocketConnection(websocket, path):
    global mapWidth, mapHeight, mapData, others, tickType, tickSpeed, activeProgram, currentRobotIndex

    async for data in websocket:
        log("Client message: " + data)
        message = json.loads(data)

        # Robot connect message
        if message["type"] == "robot_connect":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["websocket"] = websocket
            log("Robot " + str(robot["id"]) + " is connected")

            # Send world info message
            await sendWorldMessage(robot)

            # Broadcast robot connect message
            await broadcastMessage("robot_connect", {
                "robot_id": robot["id"],
                "robot": {
                    "x": robot["x"],
                    "y": robot["y"],
                    "lift": robot["lift"],
                    "color": robot["color"],
                    "directions": robot["directions"]
                }
            })

            # Send robot connected message from other robots
            for otherRobot in robots:
                if otherRobot["websocket"] != None and otherRobot["id"] != robot["id"]:
                    await sendMessage(robot, "robot_connect", {
                        "robot_id": otherRobot["id"],
                        "robot": {
                            "x": otherRobot["x"],
                            "y": otherRobot["y"],
                            "lift": otherRobot["lift"],
                            "color": otherRobot["color"],
                            "directions": otherRobot["directions"]
                        }
                    })

            # Send robot connected message from others
            for other in others:
                if other["type"] == "website":
                    await sendMessage(robot, "website_connect", { "website_id": other["id"] })

                if other["type"] == "supervisor":
                    await sendMessage(robot, "supervisor_connect", { "supervisor_id": other["id"] })

        # Website connect message
        if message["type"] == "website_connect":
            website = {
                "type": "website",
                "id": message["data"]["website_id"],
                "websocket": websocket
            }
            others.append(website)
            log("Website " + str(website["id"]) + " is connected")

            # Send world info message
            await sendWorldMessage(website)

            # Broadcast website connect message
            await broadcastMessage("website_connect", { "website_id": website["id"] })

            # Send website other robot connected messages
            for robot in robots:
                if robot["websocket"] != None:
                    await sendMessage(website, "robot_connect", {
                        "robot_id": robot["id"],
                        "robot": {
                            "x": robot["x"],
                            "y": robot["y"],
                            "lift": robot["lift"],
                            "color": robot["color"],
                            "directions": robot["directions"]
                        }
                    })

            # Send website others connected messages
            for other in others:
                if other["type"] == "website" and website["id"] != other["id"]:
                    await sendMessage(website, "website_connect", { "website_id": other["id"] })

                if other["type"] == "supervisor":
                    await sendMessage(website, "supervisor_connect", { "supervisor_id": other["id"] })

        # Supervisor connect message
        if message["type"] == "supervisor_connect":
            supervisor = {
                "type": "supervisor",
                "id": message["data"]["supervisor_id"],
                "websocket": websocket
            }
            others.append(supervisor)
            log("Supervisor " + str(supervisor["id"]) + " is connected")

            # Create map if it isn't exesting
            if mapData == None:
                mapWidth = message["data"]["map"]["width"]
                mapHeight = message["data"]["map"]["height"]

                # Create map data
                mapData = [[TILE_UNKOWN] * mapWidth for i in range(mapHeight)]
                mapData[0][0] = TILE_FLOOR
                mapData[0][mapWidth - 1] = TILE_FLOOR
                mapData[mapHeight - 1][0] = TILE_FLOOR
                mapData[mapHeight - 1][mapWidth - 1] = TILE_FLOOR

                # Setup robots positions
                robots[1 - 1]["x"] = 0
                robots[1 - 1]["y"] = 0

                robots[2 - 1]["x"] = mapWidth - 1
                robots[2 - 1]["y"] = 0

                robots[3 - 1]["x"] = 0
                robots[3 - 1]["y"] = mapHeight - 1

                robots[4 - 1]["x"] = mapWidth - 1
                robots[4 - 1]["y"] = mapHeight - 1

            # Send world info message
            await sendWorldMessage(supervisor)

            # Broadcast supervisor connect message
            await broadcastMessage("supervisor_connect", { "supervisor_id": supervisor["id"] })

            # Send robot connected messages
            for robot in robots:
                if robot["websocket"] != None:
                    await sendMessage(supervisor, "robot_connect", {
                        "robot_id": robot["id"],
                        "robot": {
                            "x": robot["x"],
                            "y": robot["y"],
                            "lift": robot["lift"],
                            "color": robot["color"],
                            "directions": robot["directions"]
                        }
                    })

            # Send others connected messages
            for other in others:
                if other["type"] == "website":
                    await sendMessage(supervisor, "website_connect", { "website_id": other["id"] })

                if other["type"] == "supervisor" and supervisor["id"] != other["id"]:
                    await sendMessage(supervisor, "supervisor_connect", { "supervisor_id": other["id"] })

        # Update world info message
        if message["type"] == "update_world_info":
            messageData = {}

            if "tick" in message["data"]:
                messageData["tick"] = {}

                if "speed" in message["data"]["tick"]:
                    tickSpeed = message["data"]["tick"]["speed"]
                    messageData["tick"]["speed"] = tickSpeed

                if "type" in message["data"]["tick"]:
                    oldTickType = tickType
                    tickType = message["data"]["tick"]["type"]
                    messageData["tick"]["type"] = tickType

                    if oldTickType == TICK_MANUAL and tickType == TICK_AUTO:
                        Timer(tickSpeed / 1000, timerCallback, None)

            if "active_program_id" in message["data"]:
                activeProgram = next((program for program in programs if program["id"] == message["data"]["active_program_id"]), None)
                messageData["active_program_id"] = activeProgram["id"]

            await broadcastMessage("update_world_info", messageData)

        # World tick message
        if message["type"] == "world_tick" and tickType == TICK_MANUAL:
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
            await broadcastMessage("new_direction", {
                "robot_id": robot["id"],
                "direction": {
                    "id": message["data"]["direction"]["id"],
                    "x": message["data"]["direction"]["x"],
                    "y": message["data"]["direction"]["y"]
                }
            })

        # Cancel direction message
        if message["type"] == "cancel_direction":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            robot["directions"] = [direction for direction in robot["directions"] if direction["id"] != message["data"]["direction_id"]]

            log("Cancel direction for Robot " + str(robot["id"]))
            await broadcastMessage("cancel_direction", {
                "robot_id": robot["id"],
                "direction_id": message["data"]["direction_id"]
            })

        # Read sensors message
        if message["type"] == "read_sensors":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            for other in others:
                if other["type"] == "supervisor":
                    messageData = { "robot_id": robot["id"] }
                    if "robot" in message["data"]:
                        robot["x"] = message["data"]["robot"]["x"]
                        robot["y"] = message["data"]["robot"]["y"]
                        messageData["robot"] = {
                            "x": robot["x"],
                            "y": robot["y"]
                        }

                    log("Read sensors from Robot " + str(robot["id"]))
                    await sendMessage(other, "read_sensors", messageData)
                    break

        # Read sensors done message
        if message["type"] == "read_sensors_done":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            log("Read sensors done for Robot " + str(robot["id"]))
            await sendMessage(robot, "read_sensors_done", {
                "robot_id": robot["id"],
                "sensors": {
                    "up": message["data"]["sensors"]["up"],
                    "left": message["data"]["sensors"]["left"],
                    "right": message["data"]["sensors"]["right"],
                    "down": message["data"]["sensors"]["down"]
                }
            })

        # Robot tick done message
        if message["type"] == "robot_tick_done":
            robot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
            messageData = { "robot_id": robot["id"] }

            if "robot" in message["data"]:
                robot["x"] = message["data"]["robot"]["x"]
                robot["y"] = message["data"]["robot"]["y"]
                messageData["robot"] = {
                    "x": robot["x"],
                    "y": robot["y"]
                }

            if "map" in message["data"]:
                messageData["map"] = []
                for mapUpdate in message["data"]["map"]:
                    if mapData[mapUpdate["y"]][mapUpdate["x"]] == TILE_UNKOWN and mapUpdate["type"] != TILE_UNKOWN:
                        mapData[mapUpdate["y"]][mapUpdate["x"]] = mapUpdate["type"]
                        messageData["map"].append({ "x": mapUpdate["x"], "y": mapUpdate["y"], "type": mapUpdate["type"] })

            log("Tick done from Robot " + str(robot["id"]))
            await broadcastMessage("robot_tick_done", messageData)

            if currentRobotIndex < len(robots):
                log("Tick for Robot " + str(robots[currentRobotIndex]["id"]))
                await broadcastMessage("robot_tick", { "robot_id": robots[currentRobotIndex]["id"] })
                currentRobotIndex += 1

    # Disconnect message for robots
    for robot in robots:
        if robot["websocket"] == websocket:
            robot["websocket"] = None
            log("Robot " + str(robot["id"]) + " is disconnected")
            await broadcastMessage("robot_disconnect", { "robot_id": robot["id"] })
            break

    # Disconnect message for others
    for other in others:
        if other["websocket"] == websocket:
            other_id = other["id"]
            others = [other for other in others if other["id"] != other_id]

            if other["type"] == "website":
                log("Website " + str(other_id) + " is disconnected")
                await broadcastMessage("website_disconnect", { "website_id": other_id })

            if other["type"] == "supervisor":
                log("Supervisor " + str(other_id) + " is disconnected")
                await broadcastMessage("supervisor_disconnect", { "supervisor_id": other_id })

            break

# Create websockets server
async def websocketsServer():
    log("Websockets server is listening at ws://127.0.0.1:" + str(WEBSOCKETS_PORT) + "/")
    async with websockets.serve(websocketConnection, "127.0.0.1", WEBSOCKETS_PORT):
        await asyncio.Future()

asyncio.run(websocketsServer())
