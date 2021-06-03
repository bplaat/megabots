#!/usr/bin/env python

# MegaBots Webots Supervisor Simulator

import asyncio
import json
import time
import websockets

# Constants
DEBUG = False

SUPERVISOR_ID = round(time.time() * 1000)

WEBSOCKETS_URL = "ws://127.0.0.1:8080/"

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

# Load map from file
mapFile = open("../../map.json", "r")
mapFileData = json.loads(mapFile.read())
mapFile.close()
mapWidth = mapFileData["width"]
mapHeight = mapFileData["height"]
mapData = mapFileData["data"]

# Robots
robots = [
    { "id": 1, "x": None, "y": None, "connected": False },
    { "id": 2, "x": None, "y": None, "connected": False },
    { "id": 3, "x": None, "y": None, "connected": False },
    { "id": 4, "x": None, "y": None, "connected": False }
]

# Simple log function
def log(line):
    if DEBUG:
        print("[SUPERVISOR] " + line)

# Websocket server connection
async def websocketConnection():
    log("Connecting with the websockets server at " + WEBSOCKETS_URL + "...")
    async with websockets.connect(WEBSOCKETS_URL) as websocket:
        async def sendMessage(type, data = {}):
            await websocket.send(json.dumps({
                "type": type,
                "data": data
            }, separators=(",", ":")))

        # Send supervisor connect message
        await sendMessage("supervisor_connect", {
            "supervisor_id": SUPERVISOR_ID,
            "map": {
                "width": mapWidth,
                "height": mapHeight
            }
        })

        async for data in websocket:
            log("Server message: " + data)
            message = json.loads(data)

            # Robot connect message
            if message["type"] == "robot_connect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["x"] = message["data"]["robot"]["x"]
                otherRobot["y"] = message["data"]["robot"]["y"]
                otherRobot["connected"] = True
                log("Robot " + str(otherRobot["id"]) + " is connected")

            # Robot disconnect message
            if message["type"] == "robot_disconnect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["connected"] = False
                log("Robot " + str(otherRobot["id"]) + " is disconnected")

            # Read sensors message
            if message["type"] == "read_sensors":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                if "robot" in message["data"]:
                    otherRobot["x"] = message["data"]["robot"]["x"]
                    otherRobot["y"] = message["data"]["robot"]["y"]

                log("Read sensors from Robot " + str(otherRobot["id"]))
                await sendMessage("read_sensors_done", {
                    "robot_id": otherRobot["id"],
                    "sensors": {
                        "up": otherRobot["y"] == 0 or mapData[otherRobot["y"] - 1][otherRobot["x"]] == TILE_CHEST,
                        "left": otherRobot["x"] == 0 or mapData[otherRobot["y"]][otherRobot["x"] - 1] == TILE_CHEST,
                        "right": otherRobot["x"] == mapWidth - 1 or mapData[otherRobot["y"]][otherRobot["x"] + 1] == TILE_CHEST,
                        "down": otherRobot["y"] == mapHeight - 1 or mapData[otherRobot["y"] + 1][otherRobot["x"]] == TILE_CHEST
                    }
                })

            # Robot tick done message
            if message["type"] == "robot_tick_done":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                if "robot" in message["data"]:
                    otherRobot["x"] = message["data"]["robot"]["x"]
                    otherRobot["y"] = message["data"]["robot"]["y"]
                log("Tick done from Robot " + str(otherRobot["id"]))

asyncio.run(websocketConnection())
