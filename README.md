# MegaBots Deluxe!!!
Some mega bots living in a grid

## Protocol idea:
```
-- Overview:
< robot 2 { new direction }
< robot 4 { new direction }
< robot 1 { new direction }

loop {
    < robot 1 { tick }
    > { robot 1 new position + 4 map items update }
    < robot 2 { robot 1 new position + 4 map items update }
    < robot 3 { robot 1 new position + 4 map items update }
    < robot 4 { robot 1 new position + 4 map items update }
}

-- New direction
{"type":"new_direction", "data":{"x":4,"y":5}}

-- Tick
{"type":"tick", "data":{}}

-- Tick done (Robot 1 -> Server)
TILE_UNKOWN = 0
TILE_NORMAL = 1
TILE_WALL = 2

{"type":"tick_done","data":{
    "position": { "x": 4, "y": 4 },
    "map": [
        { "x": 3, "y": 4, "type": 3 },
        { "x": 5, "y": 4, "type": 3 },
        { "x": 4, "y": 3, "type": 3 },
        { "x": 4, "y": 5, "type: 3 }
    ]
}}

-- Tick done (Server -> Other robots)
{"type":"tick_done","data":{
    "robot": 1,
    "position": { "x": 4, "y": 4 },
    "map": [
        { "x": 3, "y": 4, "t": 3 },
        { "x": 5, "y": 4, "t": 3 },
        { "x": 4, "y": 3, "t": 3 },
        { "x": 4, "y": 5, "t": 3 }
    ]
}}
```
