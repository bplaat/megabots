import asyncio
import json
import websockets
from warnings import warn
import heapq

DEBUG = False

ROBOT_ID = 3
WEBSOCKETS_URL = "ws://127.0.0.1:8080/"

TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2

mapWidth = None
mapHeight = None
mapData = None

robots = [
    {"id": 1, "x": None, "y": None, "directions": [], "connected": False},
    {"id": 2, "x": None, "y": None, "directions": [], "connected": False},
    {"id": 3, "x": None, "y": None, "directions": [], "connected": False},
    {"id": 4, "x": None, "y": None, "directions": [], "connected": False}
]


class Node:
    """
    A node class for A* Pathfinding
    """

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

    def __repr__(self):
        return f"{self.position} - g: {self.g} h: {self.h} f: {self.f}"

    # defining less than for purposes of heap queue
    def __lt__(self, other):
        return self.f < other.f

    # defining greater than for purposes of heap queue
    def __gt__(self, other):
        return self.f > other.f


def return_path(current_node, start_node):
    path = []
    current = current_node
    while current is not None:
        path.append(current.position)
        current = current.parent
    return path[::-1]  # Return reversed path



def astar(start, end, withOtherRobots):
    """
    Returns a list of tuples as a path from the given start to the given end in the given maze
    :param maze:
    :param start:
    :param end:
    :return:
    """
    # make coordination as tuple
    start_as_tuple = (start["x"], start["y"])
    end_as_tuple = (end["x"], end["y"])

    # Create start and end node
    start_node = Node(None, start_as_tuple)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end_as_tuple)
    end_node.g = end_node.h = end_node.f = 0

    # Initialize both open and closed list
    open_list = []
    closed_list = []

    # Heapify the open_list and Add the start node
    heapq.heapify(open_list)
    heapq.heappush(open_list, start_node)

    # Adding a stop condition
    outer_iterations = 0
    max_iterations = (len(mapData[0]) * len(mapData) // 2)

    # what squares do we search
    adjacent_squares = ((0, -1), (0, 1), (-1, 0), (1, 0),)


    # Loop until you find the end
    while len(open_list) > 0:
        outer_iterations += 1
        for robot in robots:

            if end_as_tuple[0] == robot["x"] and end_as_tuple[1] == robot["y"] and robot["connected"]:
                print("wij zijn niet get")
                return None

        if mapData[end_as_tuple[1]][end_as_tuple[0]] == TILE_CHEST:
            print("wij zijn niet get 2")
            return None

        if outer_iterations > max_iterations:
            # if we hit this point return the path such as it is
            # it will not contain the destination
            warn("giving up on pathfinding too many iterations")
            return None

            # Get the current node
        current_node = heapq.heappop(open_list)
        closed_list.append(current_node)

        # Found the goal
        if current_node == end_node:
            return return_path(current_node, start_node)


        # Generate children
        children = []

        for new_position in adjacent_squares:  # Adjacent squares

            # Get node position
            node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

            # Make sure within range
            if node_position[1] > (len(mapData) - 1) or node_position[1] < 0 or node_position[0] > (
                    len(mapData[len(mapData) - 1]) - 1) or node_position[0] < 0:
                continue

            if withOtherRobots:
                colliding = False
                for robot in robots:
                    if robot["connected"] and robot["x"] == node_position[0] and robot["y"] == node_position[1]:
                        colliding = True
                        break
                if colliding:
                    continue


            # Make sure walkable terrain
            if mapData[node_position[1]][node_position[0]] > 1:
                continue


            # Create new node
            new_node = Node(current_node, node_position)

            # Append
            children.append(new_node)


        # Loop through children
        for child in children:
            # Child is on the closed list
            if len([closed_child for closed_child in closed_list if closed_child == child]) > 0:
                continue

            # Create the f, g, and h values
            child.g = current_node.g + 1
            child.h = ((child.position[0] - end_node.position[0]) ** 2) + (
                        (child.position[1] - end_node.position[1]) ** 2)
            child.f = child.g + child.h

            # Child is already in the open list
            if len([open_node for open_node in open_list if
                    child.position == open_node.position and child.g > open_node.g]) > 0:
                continue

            # Add the child to the open list
            heapq.heappush(open_list, child)

    warn("Couldn't get a path to destination")
    return None


def log(line):
    if DEBUG:
        print("[ROBOT " + str(ROBOT_ID) + "] " + line)


async def websocketConnection():
    global mapWidth, mapHeight, mapData

    robot = next((robot for robot in robots if robot["id"] == ROBOT_ID), None)
    tickCounter = 0

    log("Connecting with the websockets server at " + WEBSOCKETS_URL + "...")
    async with websockets.connect(WEBSOCKETS_URL) as websocket:
        async def sendMessage(type, data={}):
            await websocket.send(json.dumps({
                "type": type,
                "data": data
            }, separators=(",", ":")))

        # Send robot connect message
        await sendMessage("robot_connect", {"robot_id": robot["id"]})

        async for data in websocket:
            log("Server message: " + data)
            message = json.loads(data)

            # World info message
            if message["type"] == "world_info":
                mapWidth = message["data"]["map"]["width"]
                mapHeight = message["data"]["map"]["height"]

                # Create map data
                mapData = [[TILE_UNKOWN] * mapWidth for i in range(mapHeight)]
                mapData[0][0] = TILE_FLOOR
                mapData[0][mapWidth - 1] = TILE_FLOOR
                mapData[mapHeight - 1][0] = TILE_FLOOR
                mapData[mapHeight - 1][mapWidth - 1] = TILE_FLOOR

                # Patch map data with given map
                for y in range(mapHeight):
                    for x in range(mapWidth):
                        if mapData[y][x] == TILE_UNKOWN and message["data"]["map"]["data"][y][x] != TILE_UNKOWN:
                            mapData[y][x] = message["data"]["map"]["data"][y][x]

            # Robot connect message
            if message["type"] == "robot_connect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["x"] = message["data"]["robot"]["x"]
                otherRobot["y"] = message["data"]["robot"]["y"]
                otherRobot["directions"] = []
                for direction in message["data"]["robot"]["directions"]:
                    otherRobot["directions"].append({
                        "id": direction["id"],
                        "x": direction["x"],
                        "y": direction["y"]
                    })
                otherRobot["connected"] = True
                log("Robot " + str(otherRobot["id"]) + " is connected")

            # Robot disconnect message
            if message["type"] == "robot_disconnect":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["connected"] = False
                log("Robot " + str(otherRobot["id"]) + " is disconnected")

            # New direction message
            if message["type"] == "new_direction":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["directions"].append({
                    "id": message["data"]["direction"]["id"],
                    "x": message["data"]["direction"]["x"],
                    "y": message["data"]["direction"]["y"]
                })
                log("New direction for Robot " + str(otherRobot["id"]))

            # Cancel direction message
            if message["type"] == "cancel_direction":
                otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                otherRobot["directions"] = [direction for direction in otherRobot["directions"] if
                                            direction["id"] != message["data"]["direction_id"]]
                log("Cancel direction for robot " + str(otherRobot["id"]))

            # Read sensors done message
            if message["type"] == "read_sensors_done":
                # Patch map data with given sensor data
                mapUpdates = []

                if robot["y"] > 0:
                    upType = message["data"]["sensors"]["up"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"] - 1][robot["x"]] = upType
                    mapUpdates.append({"x": robot["x"], "y": robot["y"] - 1, "type": upType})

                if robot["x"] > 0:
                    leftType = message["data"]["sensors"]["left"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"]][robot["x"] - 1] = leftType
                    mapUpdates.append({"x": robot["x"] - 1, "y": robot["y"], "type": leftType})

                if robot["x"] < mapWidth - 1:
                    rightType = message["data"]["sensors"]["right"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"]][robot["x"] + 1] = rightType
                    mapUpdates.append({"x": robot["x"] + 1, "y": robot["y"], "type": rightType})

                if robot["y"] < mapHeight - 1:
                    downType = message["data"]["sensors"]["down"] and TILE_CHEST or TILE_FLOOR
                    mapData[robot["y"] + 1][robot["x"]] = downType
                    mapUpdates.append({"x": robot["x"], "y": robot["y"] + 1, "type": downType})

                # Send tick done message
                log("Tick done: ")
                tickCounter += 1
                await sendMessage("robot_tick_done", {
                    "robot_id": robot["id"],
                    "robot": {
                        "x": robot["x"],
                        "y": robot["y"]
                    },
                    "map": mapUpdates
                })

            # Robot tick message
            if message["type"] == "robot_tick":
                # Ignore robot tick messages for other robots
                if message["data"]["robot_id"] != robot["id"]:
                    continue

                # When it is the first tick read only sensors
                if tickCounter == 0:
                    log("First tick read only sensors")
                    await sendMessage("read_sensors", {"robot_id": robot["id"]})
                    continue

                # Do nothing because no directions
                if len(robot["directions"]) == 0:
                    log("Tick done but no directions")
                    tickCounter += 1
                    await sendMessage("robot_tick_done", {"robot_id": robot["id"]})
                    continue

                # Check if we are not already at destination
                destination = {"x": robot["directions"][0]["x"], "y": robot["directions"][0]["y"]}
                if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                    # Cancel direction because complete
                    await sendMessage("cancel_direction", {
                        "robot_id": robot["id"],
                        "direction_id": robot["directions"][0]["id"]
                    })

                    # Do nothing because direction complete
                    log("Tick done but no directions")
                    tickCounter += 1
                    await sendMessage("robot_tick_done", {"robot_id": robot["id"]})
                    continue

                # Find path to destination
                start = {"x": robot["x"], "y": robot["y"]}
                path = astar(start, destination, True)

                # If implosible check again without other robots to check if posible
                if path == None:
                    path = astar(start, destination, False)
                    if path == None:
                        # Cancel direction because path imposible
                        await sendMessage("cancel_direction", {
                            "robot_id": robot["id"],
                            "direction_id": robot["directions"][0]["id"]
                        })

                        log("Tick done but direction canceled because impossible")
                        tickCounter += 1
                        await sendMessage("robot_tick_done", {"robot_id": robot["id"]})
                    else:
                        # Don't move wait until other robots are moved on
                        log("Tick done waiting for robot to move away")
                        tickCounter += 1
                        await sendMessage("robot_tick_done", {"robot_id": robot["id"]})
                else:
                    # Move robot one step
                    robot["x"] = path[1][0]
                    robot["y"] = path[1][1]

                    # When we are at the destination delete direction
                    if robot["x"] == destination["x"] and robot["y"] == destination["y"]:
                        # Cancel direction because complete
                        await sendMessage("cancel_direction", {
                            "robot_id": robot["id"],
                            "direction_id": robot["directions"][0]["id"]
                        })

                    # Read sensors of new position
                    await sendMessage("read_sensors", {
                        "robot_id": robot["id"],
                        "robot": {
                            "x": robot["x"],
                            "y": robot["y"]
                        }
                    })

            # Robot tick done message
            if message["type"] == "robot_tick_done":
                if robot["id"] != message["data"]["robot_id"]:
                    otherRobot = next((robot for robot in robots if robot["id"] == message["data"]["robot_id"]), None)
                    if "robot" in message["data"]:
                        otherRobot["x"] = message["data"]["robot"]["x"]
                        otherRobot["y"] = message["data"]["robot"]["y"]

                    if "map" in message["data"]:
                        for mapUpdate in message["data"]["map"]:
                            if mapData[mapUpdate["y"]][mapUpdate["x"]] == TILE_UNKOWN and mapUpdate[
                                "type"] != TILE_UNKOWN:
                                mapData[mapUpdate["y"]][mapUpdate["x"]] = mapUpdate["type"]

                    log("Tick done from Robot " + str(otherRobot["id"]))


asyncio.run(websocketConnection())
