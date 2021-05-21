#!/usr/bin/env python

import sys
import json

# Constants
TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
TILE_WALL = 3

# Map generator script
mapWidth = len(sys.argv) >= 2 and int(sys.argv[1]) or 16
mapHeight = len(sys.argv) >= 2 and int(sys.argv[2]) or 16
mapData = [TILE_UNKOWN] * (mapHeight * mapWidth)

for y in range(mapHeight):
    for x in range(mapWidth):
        if x == 0 or y == 0 or x == mapWidth - 1 or y == mapHeight - 1:
            mapData[y * mapWidth + x] = TILE_WALL
        elif (
            (x == 1 and y == 1) or
            (x == mapWidth - 2 and y == 1) or
            (x == 1 and y == mapHeight - 2) or
            (x == mapWidth - 2 and y == mapHeight - 2)
        ):
            mapData[y * mapWidth + x] = TILE_FLOOR
        else:
            if (x + y) % 3 or x == 1 or y == 1 or x == mapWidth - 2 or y == mapHeight - 2:
                mapData[y * mapWidth + x] = TILE_FLOOR
            else:
                mapData[y * mapWidth + x] = TILE_CHEST

# Write map data to JSON file
with open("map.json", "w") as mapFile:
    mapFile.write(json.dumps({
        "type": "MegaBots Map",
        "width": mapWidth,
        "height": mapHeight,
        "data": mapData
    }))
