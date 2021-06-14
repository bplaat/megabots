
import asyncio
import json
import random
import sys
import websockets

# mijn Robot id
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

###### BEGIN PATHFINDING ######
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

###### END PATHFINDING ######


#Plek om al de robots in op te slaan.
robots = [
    { "id": 1, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 2, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 3, "x": None, "y": None, "directions": [], "connected": False },
    { "id": 4, "x": None, "y": None, "directions": [], "connected": False }
]


#Zet de verbinding op met de server
async def websocketConnection():
    global mapWidth, mapHeight, mapData

    robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
    tickCounter = 0

    print("Starting connection: " + WEBSOCKETS_URL)
    async with websockets.connect(WEBSOCKETS_URL) as websocket:
        async def sendMessage(type, data = {}):
            await websocket.send(json.dumps({"type": type, "data": data},
            seperators=(",", ":")))


        #Stuur het bericht om te verbinden met de server conform met het protocol
        await sendMessage("robot_connect", { "robot_id": robot["id"]})

        #Ontvangt en print het bericht, stopt het bericht dan in message.
        #Daarna veel if statements voor de verschillende mogelijke berichten
        async for data in websocket:
            print(data)
            message = json.loads(data)



        #Als het een world_info bericht is
        #Door een world_info bericht maken we de wereld
        if message["type"] == "world_info":
            mapWidth = message["data"]["map"]["width"]
            mapHeight = message["data"]["map"]["height"]

            #Maak de wereld en vul het met unknown tiles
            mapData = [[TILE_UNKOWN] * mapWidth for i in range(mapHeight)]
            #Voor ons al bekende vloer tegels, omdat dit de 4 hoeken van de wereld zijn
            mapData[0][0] = TILE_FLOOR
            mapData[mapHeight - 1][mapWidth - 1] = TILE_FLOOR
            mapData[0][mapWidth - 1] = TILE_FLOOR
            mapData[mapHeight -1][0] = TILE_FLOOR


        #Wanneer een andere robot met ons verbind
        if message["type"] == "robot_connect":
            pass


        #Wanneer een andere robot de verbinding verbreekt
        if message["type"] == "robot_disconnect":
            pass


        #Wanneer de server ons een nieuwe richting op stuurt
        if message["type"] == "new_direction":
            pass



        #Wanneer de server onze huidige richting stopt
        if message["type"] == "cancel_direction":
            pass



        #Wanneer de sensoren van de robot uitgelezen zijn
        if message["type"] == "read_sensors_done":
            pass


        #wanneer een andere robot zijn tick uitvoerd
        if message["type"] == "robot_tick":
            pass


        #Bericht wanneer een andere robot zijn tick heeft uitgevoerd
        if message ["type"] ==  "robot_tick_done":
            pass

asyncio.run(websocketConnection())
