#!/usr/bin/env python

# MegaBots Webots Supervisor

import asyncio
from controller import Supervisor
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

# Robots
supervisor = Supervisor()
robots = [
    { "id": 1, "x": None, "y": None, "connected": False },
    { "id": 2, "x": None, "y": None, "connected": False },
    { "id": 3, "x": None, "y": None, "connected": False },
    { "id": 4, "x": None, "y": None, "connected": False }
]

# Load map from webots world
arena = supervisor.getFromDef("arena")
arenaFloorSize = arena.getField("floorSize").getSFVec2f()
mapWidth = round(arenaFloorSize[0] * 10)
mapHeight = round(arenaFloorSize[1] * 10)

mapData = [[TILE_FLOOR] * mapWidth for i in range(mapHeight)]
chests = supervisor.getFromDef("chests").getField("children")
for i in range(chests.getCount()):
    chest = chests.getMFNode(i)
    chestPosition = chest.getField("translation").getSFVec3f()
    mapData[round((chestPosition[2] - 0.05) * 10 + mapHeight / 2)][round((chestPosition[0] - 0.05) * 10 + mapWidth / 2)] = TILE_CHEST

def updateRobotPosition(robot, x, y):
    oldRobotX = robot["x"]
    oldRobotY = robot["y"]
    robot["x"] = x
    robot["y"] = y

    robotNode = supervisor.getFromDef("robot_" + str(robot["id"]))
    robotNode.getField("translation").setSFVec3f([
        (robot["x"] - mapWidth / 2) / 10 + 0.05,
        0.05,
        (robot["y"] - mapHeight / 2) / 10 + 0.05
    ])

    if oldRobotX != None and oldRobotY != None:
        upLedNode = supervisor.getFromDef("robot_" + str(robot["id"]) + "_up_led")
        if robot["y"] - oldRobotY < 0:
            upLedNode.getField("diffuseColor").setSFColor([ 1, 1, 1 ])
        else:
            upLedNode.getField("diffuseColor").setSFColor([ 0, 0, 0 ])

        leftLedNode = supervisor.getFromDef("robot_" + str(robot["id"]) + "_left_led")
        if robot["x"] - oldRobotX < 0:
            leftLedNode.getField("diffuseColor").setSFColor([ 1, 1, 1 ])
        else:
            leftLedNode.getField("diffuseColor").setSFColor([ 0, 0, 0 ])

        rightLedNode = supervisor.getFromDef("robot_" + str(robot["id"]) + "_right_led")
        if robot["x"] - oldRobotX > 0:
            rightLedNode.getField("diffuseColor").setSFColor([ 1, 1, 1 ])
        else:
            rightLedNode.getField("diffuseColor").setSFColor([ 0, 0, 0 ])

        downLedNode = supervisor.getFromDef("robot_" + str(robot["id"]) + "_down_led")
        if robot["y"] - oldRobotY > 0:
            downLedNode.getField("diffuseColor").setSFColor([ 1, 1, 1 ])
        else:
            downLedNode.getField("diffuseColor").setSFColor([ 0, 0, 0 ])

    supervisor.step(int(supervisor.getBasicTimeStep()))

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
                updateRobotPosition(otherRobot, message["data"]["robot"]["x"], message["data"]["robot"]["y"])
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

                robotX = otherRobot["x"]
                robotY = otherRobot["y"]
                if "robot" in message["data"]:
                    robotX = message["data"]["robot"]["x"]
                    robotY = message["data"]["robot"]["y"]

                log("Read sensors from Robot " + str(otherRobot["id"]))
                await sendMessage("read_sensors_done", {
                    "robot_id": otherRobot["id"],
                    "sensors": {
                        "up": robotY == 0 or mapData[robotY - 1][robotX] == TILE_CHEST,
                        "left": robotX == 0 or mapData[robotY][robotX - 1] == TILE_CHEST,
                        "right": robotX == mapWidth - 1 or mapData[robotY][robotX + 1] == TILE_CHEST,
                        "down": robotY == mapHeight - 1 or mapData[robotY + 1][robotX] == TILE_CHEST
                    }
                })

            # Robot tick done message
            if message["type"] == "robot_tick_done":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                if "robot" in message["data"]:
                    updateRobotPosition(otherRobot, message["data"]["robot"]["x"], message["data"]["robot"]["y"])
                else:
                    updateRobotPosition(otherRobot, otherRobot["x"], otherRobot["y"])
                log("Tick done from Robot " + str(otherRobot["id"]))

asyncio.run(websocketConnection())
