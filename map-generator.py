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
if len(sys.argv) >= 4 and sys.argv[3] == "webots":
    # Robots start in the corners
    robots = [
        { "id": 1, "x": 0, "y": 0, "color": { "red": 1, "green": 0, "blue": 0 } },
        { "id": 2, "x": mapWidth - 1, "y": 0, "color": { "red": 0, "green": 1, "blue": 0 } },
        { "id": 3, "x": 0, "y": mapHeight - 1, "color": { "red": 1, "green": 1, "blue": 0 } },
        { "id": 4, "x": mapWidth - 1, "y": mapHeight - 1, "color": { "red": 0, "green": 0, "blue": 1 } }
    ]

    # Create webots world file
    with open("webots/worlds/world.wbt", "w") as worldFile:
        # Create world and rectangle arena
        worldFile.write("""#VRML_SIM R2021a utf8
WorldInfo {
    basicTimeStep 100
    coordinateSystem "NUE"
}
Viewpoint {
    orientation -0.8 0.5 0.25 1.0072345104625866
    position %f %f %f
}
TexturedBackground {
}
TexturedBackgroundLight {
}
DEF arena RectangleArena {
    translation 0 0 0
    floorSize %f %f
    floorTileSize 0.2 0.2
    wallHeight 0.05
}
DEF chests Group {
    children [
    """ % (
    mapWidth / 10,
    mapHeight / 10,
    mapWidth / 10,
    mapWidth / 10,
    mapHeight / 10
))

        # Add chests of random maze
        chestCounter = 0
        for y in range(0, mapHeight):
            for x in range(0, mapWidth):
                if mapData[y][x] == TILE_CHEST:
                    worldFile.write("""WoodenBox {
    name "Chest %d"
    translation %f 0.05 %f
    size 0.1 0.1 0.1
}
""" % (
    chestCounter,
    (x - mapWidth / 2) / 10 + 0.05,
    (y - mapHeight / 2) / 10 + 0.05
))
                    chestCounter += 1

        worldFile.write("""]
}
""")

        # Add robots
        for robot in robots:
            worldFile.write("""DEF robot_%d Robot {
    name "robot_%d"
    translation %f 0.05 %f
    children [
        Solid {
            children [
                DEF robot_%d_shape Shape {
                    appearance Appearance {
                        material Material {
                            diffuseColor %f %f %f
                        }
                    }
                    geometry Cylinder {
                        height 0.1
                        radius 0.025
                    }
                }
            ]
        }

        Solid {
            name "robot_%d_up_led"
            translation 0 0.05 -0.02
            children [
                Shape {
                    appearance Appearance {
                        material DEF robot_%d_up_led Material {
                            diffuseColor 0 0 0
                        }
                    }
                    geometry Sphere {
                        radius 0.0075
                    }
                }
            ]
        }

        Solid {
            name "robot_%d_left_led"
            translation -0.02 0.05 0
            children [
                Shape {
                    appearance Appearance {
                        material DEF robot_%d_left_led Material {
                            diffuseColor 0 0 0
                        }
                    }
                    geometry Sphere {
                        radius 0.0075
                    }
                }
            ]
        }

        Solid {
            name "robot_%d_right_led"
            translation 0.02 0.05 0
            children [
                Shape {
                    appearance Appearance {
                        material DEF robot_%d_right_led Material {
                            diffuseColor 0 0 0
                        }
                    }
                    geometry Sphere {
                        radius 0.0075
                    }
                }
            ]
        }

        Solid {
            name "robot_%d_down_led"
            translation 0 0.05 0.02
            children [
                Shape {
                    appearance Appearance {
                        material DEF robot_%d_down_led Material {
                            diffuseColor 0 0 0
                        }
                    }
                    geometry Sphere {
                        radius 0.0075
                    }
                }
            ]
        }
    ]
    boundingObject USE robot_%d_shape
    %s
}
""" % (
    robot["id"],
    robot["id"],
    (robot["x"] - mapWidth / 2) / 10 + 0.05,
    (robot["y"] - mapHeight / 2) / 10 + 0.05,

    robot["id"],
    robot["color"]["red"],
    robot["color"]["green"],
    robot["color"]["blue"],

    robot["id"],
    robot["id"],

    robot["id"],
    robot["id"],

    robot["id"],
    robot["id"],

    robot["id"],
    robot["id"],

    robot["id"],
    robot["id"] == 1 and """supervisor TRUE
controller "supervisor"
""" or ""
            ))
