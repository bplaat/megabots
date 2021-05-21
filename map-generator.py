#!/usr/bin/env python

import sys
import json
import random

# Constants
TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
TILE_WALL = 3

# Simple Python Maze generator more info:
# https://rosettacode.org/wiki/Maze_generation#Python
def makeMaze(w, h):
    vis = [[0] * w + [1] for _ in range(h)] + [[1] * (w + 1)]
    ver = [["|  "] * w + ['|'] for _ in range(h)] + [[]]
    hor = [["+--"] * w + ['+'] for _ in range(h + 1)]

    def walk(x, y):
        vis[y][x] = 1

        d = [(x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)]
        random.shuffle(d)
        for (xx, yy) in d:
            if vis[yy][xx]: continue
            if xx == x: hor[max(y, yy)][x] = "+  "
            if yy == y: ver[y][max(x, xx)] = "   "
            walk(xx, yy)

    walk(random.randrange(w), random.randrange(h))

    s = ""
    for (a, b) in zip(hor, ver):
        s += ''.join(a + ['\n'] + b + ['\n'])
    return s

# Map generator script
mapWidth = len(sys.argv) >= 2 and int(sys.argv[1]) or 16
mapHeight = len(sys.argv) >= 2 and int(sys.argv[2]) or 16
mapData = [TILE_UNKOWN] * (mapHeight * mapWidth)

for y in range(mapHeight):
    for x in range(mapWidth):
        if x == 0 or y == 0 or x == mapWidth - 1 or y == mapHeight - 1:
            mapData[y * mapWidth + x] = TILE_WALL
        else:
            mapData[y * mapWidth + x] = TILE_FLOOR

# Generate random maze and copy into map data
maze = makeMaze(32, 32)
lines = maze.split('\n')
print("Maze line length: " + str(len(lines[0])))
for y in range(2, mapHeight - 2):
    for x in range(2, mapWidth - 2):
        mapData[y * mapWidth + x] = lines[y][x] == " " and TILE_FLOOR or TILE_CHEST

# Write map data to JSON file
with open("map.json", "w") as mapFile:
    mapFile.write(json.dumps({
        "type": "MegaBots Map",
        "width": mapWidth,
        "height": mapHeight,
        "data": mapData
    }))
