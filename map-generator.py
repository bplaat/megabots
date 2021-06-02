#!/usr/bin/env python

import json
import math
import os
import random
import sys

# Constants
TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

# Simple Python Maze generator more info:
# https://rosettacode.org/wiki/Maze_generation#Python
def makeMaze(w, h):
    vis = [[0] * w + [1] for _ in range(h)] + [[1] * (w + 1)]
    ver = [["| "] * w + ["|"] for _ in range(h)] + [[]]
    hor = [["+-"] * w + ["+"] for _ in range(h + 1)]

    def walk(x, y):
        vis[y][x] = 1

        d = [(x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)]
        random.shuffle(d)
        for (xx, yy) in d:
            if vis[yy][xx]: continue
            if xx == x: hor[max(y, yy)][x] = "+ "
            if yy == y: ver[y][max(x, xx)] = "  "
            walk(xx, yy)

    walk(random.randrange(w), random.randrange(h))

    s = ""
    for (a, b) in zip(hor, ver):
        s += "".join(a + ["\n"] + b + ["\n"])
    return s

# Map generator script
mapWidth = len(sys.argv) >= 2 and min(int(sys.argv[1]), 64) or 16
mapHeight = len(sys.argv) >= 2 and min(int(sys.argv[2]), 64) or 16
mapData = [[TILE_FLOOR] * mapWidth for i in range(mapHeight)]

# Generate random maze and copy into map data
maze = makeMaze(34, 34)
lines = maze.split("\n")
for y in range(1, mapHeight - 1):
    for x in range(1, mapWidth - 1):
        mapData[y][x] = lines[y + 1][x + 1] == " " and TILE_FLOOR or TILE_CHEST

# Write map data to JSON file
with open("webots/map.json", "w") as mapFile:
    mapFile.write(json.dumps({
        "type": "MegaBots Map",
        "width": mapWidth,
        "height": mapHeight,
        "data": mapData
    }, separators=(",", ":")))

###################################################
############# Webots world generation #############
###################################################
# if len(sys.argv) >= 4 and sys.argv[3] == "webots":
#     # Robots start in the corners
#     robots = [
#         { "id": 1, "name": "bastiaan", "x": 0, "y": 0, },
#         { "id": 2, "name": "bastiaan", "x": mapWidth - 1, "y": 0 },
#         { "id": 3, "name": "bastiaan", "x": 0, "y": mapHeight - 1 },
#         { "id": 4, "name": "bastiaan", "x": mapWidth - 1, "y": mapHeight - 1 }
#     ]

#     # Create webots world file
#     os.makedirs("webots/controllers", exist_ok=True)
#     os.makedirs("webots/worlds", exist_ok=True)
#     with open("webots/worlds/world.wbt", "w") as worldFile:
#         # Create world and rectangle arena
#         worldFile.write("""#VRML_SIM R2021a utf8
# WorldInfo {
#     basicTimeStep 100
#     coordinateSystem "NUE"
# }
# Viewpoint {
#     orientation -0.8 0.5 0.25 1.0072345104625866
#     position %f %f %f
# }
# TexturedBackground {
# }
# TexturedBackgroundLight {
# }
# RectangleArena {
#     translation 0 0 0
#     floorSize %f %f
#     floorTileSize 0.2 0.2
#     wallHeight 0.05
# }
# Group {
#     children [
#     """ % (mapWidth / 10, mapHeight / 10, mapWidth / 10, mapWidth / 10, mapHeight / 10))

#         # Add chests of random maze
#         chestCounter = 0
#         for y in range(0, mapHeight):
#             for x in range(0, mapWidth):
#                 if mapData[y * mapWidth + x] == TILE_CHEST:
#                     worldFile.write("""WoodenBox {
#     name "Chest %d"
#     translation %f 0.05 %f
#     size 0.1 0.1 0.1
# }
# """ % (chestCounter, (x - mapWidth / 2) / 10 + 0.05, (y - mapHeight / 2) / 10 + 0.05))
#                     chestCounter += 1

#         worldFile.write("""]
# }
# """)

#         # Add robots
#         for robot in robots:
#             worldFile.write("""Robot {
#     name "Robot %d"
#     translation %f 0.05 %f
#     children [
#         Solid {
#             children [
#                 DEF robot_%d_shape Shape {
#                     appearance Appearance {
#                         material Material {
#                         }
#                         texture ImageTexture {
#                             url [
#                                 "../../server/website/images/robot.jpg"
#                             ]
#                         }
#                     }
#                     geometry Cylinder {
#                         height 0.1
#                         radius 0.025
#                     }
#                 }
#             ]
#         }
#         DistanceSensor {
#             name "Distance Right Sensor"
#             rotation 0 0 0 %f
#         }
#         DistanceSensor {
#             name "Distance Up Sensor"
#             rotation 0 0 0 %f
#         }
#         DistanceSensor {
#             name "Distance Left Sensor"
#             rotation 0 0 0 %f
#         }
#         DistanceSensor {
#             name "Distance Down Sensor"
#             rotation 0 0 0 %f
#         }
#     ]
#     boundingObject USE robot_%d_shape
#     supervisor TRUE
#     controller "robot_%d_controller"
# }
# """ % (
#                 robot["id"],
#                 (robot["x"] - mapWidth / 2) / 10 + 0.05, (robot["y"] - mapHeight / 2) / 10 + 0.05,
#                 robot["id"],
#                 0,
#                 math.pi * 0.5,
#                 math.pi,
#                 math.pi * 1.5,
#                 robot["id"],
#                 robot["id"]
#             ))


#             # Create controller python file
#             os.makedirs("webots/controllers/robot_%d_controller" % (robot["id"]), exist_ok=True)

#             with open("webots/controllers/robot_%d_controller/robot_%d_controller.py" % (robot["id"], robot["id"]), "w") as controllerFile:
#                 controllerFile.write("""from controller import Supervisor
# import asyncio
# import json
# import os
# import sys
# import threading
# sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../../../clients/%s")
# import client
# sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../../../clients")
# import events

# # Load map from file
# mapFile = open(os.path.dirname(os.path.realpath(__file__)) + "/../../../map.json", "r")
# mapFileData = json.loads(mapFile.read())
# mapWidth = mapFileData["width"]
# mapHeight = mapFileData["height"]
# mapData = mapFileData["data"]
# mapFile.close()

# robot = Supervisor()
# robotNode = robot.getSelf()
# translation = robotNode.getField("translation")

# async def robotController():
#     robotId = %d
#     robotX = None
#     robotY = None

#     # distanceUpSensor = robot.getDevice("Distance Up Sensor")
#     # distanceUpSensor.enable(100)
#     # distanceLeftSensor = robot.getDevice("Distance Left Sensor")
#     # distanceLeftSensor.enable(100)
#     # distanceRightSensor = robot.getDevice("Distance Right Sensor")
#     # distanceRightSensor.enable(100)
#     # distanceBottomSensor = robot.getDevice("Distance Bottom Sensor")
#     # distanceBottomSensor.enable(100)

#     # Listen to sensors callbacks
#     async def sensorsCallback(data):
#         global robotX, robotY
#         print("sensors", robotX, robotY)
#         mapUpdates = []
#         # print("Up:", distanceUpSensor.getValue())
#         # print("Left:", distanceLeftSensor.getValue())
#         # print("Right:", distanceRightSensor.getValue())
#         # print("Bottom:", distanceBottomSensor.getValue())

#         if robotX > 0:
#             mapUpdates.append({ "x": robotX - 1, "y": robotY, "type": mapData[robotY * mapWidth + (robotX - 1)] })
#         if robotX < mapWidth - 1:
#             mapUpdates.append({ "x": robotX + 1, "y": robotY, "type": mapData[robotY * mapWidth + (robotX + 1)] })
#         if robotY > 0:
#             mapUpdates.append({ "x": robotX, "y": robotY - 1, "type": mapData[(robotY - 1) * mapWidth + robotX] })
#         if robotY < mapHeight - 1:
#             mapUpdates.append({ "x": robotX, "y": robotY + 1, "type": mapData[(robotY + 1) * mapWidth + robotX] })
#         await events.send("sensors_response", { "map_updates": mapUpdates })
#     events.on("sensors", sensorsCallback)

#     # Listen to move events to update local robot position
#     async def moveCallback(data):
#         global robotX, robotY
#         robotX = data["robot_x"]
#         robotY = data["robot_y"]
#         print("move", robotX, robotY)
#         translation.setSFVec3f([ (robotX - mapWidth / 2) / 10 + 0.05, 0.05, (robotY - mapHeight / 2) / 10 + 0.05 ])
#     events.on("move", moveCallback)

#     # Send start message last to start connection (no return because async websocket connection!)
#     await events.send("start", { "robot_id": robotId })

# def stepperThread():
#     while robot.step(1000) != -1:
#         # print("tick")
#         pass

# thread = threading.Thread(target=stepperThread)
# thread.start()

# asyncio.run(robotController())
# """ % (robot["name"], robot["id"]))
