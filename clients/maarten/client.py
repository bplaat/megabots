
import asyncio
import json
import random
import sys
import websockets


ROBOT_ID = 3

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
    cameFrom =  [[None] * mapWidth for i in range(mapHeight)]

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
                    if robot["connected"] and robot["x"] == neighbor["x"] and robot["y"] == neighbor["y"]:
                        colliding = True
                        break
                if colliding:
                    continue

            # Ignore chest tiles
            tileType = mapData[neighbor["y"]][neighbor["x"]]
            if not (tileType == TILE_FLOOR or tileType == TILE_UNKOWN):
                continue

            # Add tile to came from point map
            if cameFrom[neighbor["y"]][neighbor["x"]] == None:
                frontier.append(neighbor)
                cameFrom[neighbor["y"]][neighbor["x"]] = current

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
        current = cameFrom[current["y"]][current["x"]]
    path.reverse()
    return path

robots = [
    { "id": 1, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 2, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 3, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 4, "x": None, "y": None, "directions": [], "connected": False }
]
