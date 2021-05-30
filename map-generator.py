#!/usr/bin/env python

import json
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
    ver = [["| "] * w + ['|'] for _ in range(h)] + [[]]
    hor = [["+-"] * w + ['+'] for _ in range(h + 1)]

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
        s += ''.join(a + ['\n'] + b + ['\n'])
    return s

# Map generator script
mapWidth = len(sys.argv) >= 2 and min(int(sys.argv[1]), 64) or 16
mapHeight = len(sys.argv) >= 2 and min(int(sys.argv[2]), 64) or 16
mapData = [TILE_FLOOR] * (mapHeight * mapWidth)

# Generate random maze and copy into map data
maze = makeMaze(34, 34)
lines = maze.split('\n')
for y in range(1, mapHeight - 1):
    for x in range(1, mapWidth - 1):
        mapData[y * mapWidth + x] = lines[y][x] == " " and TILE_FLOOR or TILE_CHEST

# Write map data to JSON file
with open("map.json", "w") as mapFile:
    mapFile.write(json.dumps({
        "type": "MegaBots Map",
        "width": mapWidth,
        "height": mapHeight,
        "data": mapData
    }, separators=(',', ':')))

# Create webots world file
with open("webots/world.wbt", "w") as webotsFile:
    webotsFile.write("""#VRML_SIM R2021a utf8
WorldInfo {
    basicTimeStep 100
    coordinateSystem "NUE"
}
Viewpoint {
    orientation -0.8105251800653819 0.5320768237455532 0.24483297595059322 1.0072345104625866
    position %f %f %f
}
TexturedBackground {
}
TexturedBackgroundLight {
}
RectangleArena {
    translation 0 0 0
    floorSize %f %f
    floorTileSize 0.1 0.1
    WallHeight 0.05
}
""" % (mapWidth / 10, mapHeight / 10, mapWidth / 10, mapWidth / 10, mapHeight / 10))

    chestCounter = 0
    for y in range(0, mapHeight):
        for x in range(0, mapWidth):
            if mapData[y * mapWidth + x] == TILE_CHEST:
                webotsFile.write("""WoodenBox {
    name "Chest #%d"
    translation %f 0.05 %f
    size 0.1 0.1 0.1
}
""" % (chestCounter, (x - mapWidth / 2) / 10 + 0.05, (y - mapHeight / 2) / 10 + 0.05))
                chestCounter += 1
