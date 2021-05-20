# MegaBots Deluxe!!!
Some mega bots living in a grid

## Run the server and clients:
- Install the websockets Python package:

    ```
    pip install websockets
    ```

- Run the `test.sh` script to start all processes:

    ```
    ./test.sh
    ```

## Protocol idea:
```
-- Overview:
> robot 1 { connect }
< robot 2 { connect }
< robot 3 { connect }
< robot 4 { connect }

> robot 2 { direction }
< robot 1 { direction }
< robot 3 { direction }
< robot 4 { direction }

loop {
    < robot 1 { tick }
    < robot 2 { tick }
    < robot 3 { tick }
    < robot 4 { tick }
    > robot 1 { tick_done }
    < robot 2 { tick_done }
    < robot 3 { tick_done }
    < robot 4 { tick_done }
}

# Robot 1 disconnects
< robot 2 { disconnect }
< robot 3 { disconnect }
< robot 4 { disconnect }

-- Connect message
{"type":"connect","data":{"id":1}}

-- Disconnect message
{"type":"disconnect","data":{"id":1}}

-- Direction message
{"type":"direction","data":{"id":1,"x":4,"y":5}}

-- Tick message
{"type":"tick","data":{"id":1}}

-- Tick done (Robot 1 -> Server) message
TILE_UNKOWN = 0
TILE_NORMAL = 1
TILE_WALL = 2

{"type":"tick_done","data":{
    "id": 1,
    "position": { "x": 4, "y": 4 },
    "map": [
        { "x": 3, "y": 4, "type": 3 },
        { "x": 5, "y": 4, "type": 3 },
        { "x": 4, "y": 3, "type": 3 },
        { "x": 4, "y": 5, "type": 3 }
    ]
}}

-- Tick done (Server -> Other robots) message
{"type":"tick_done","data":{
    "id": 1,
    "position": { "x": 4, "y": 4 },
    "map": [
        { "x": 3, "y": 4, "type": 3 },
        { "x": 5, "y": 4, "type": 3 },
        { "x": 4, "y": 3, "type": 3 },
        { "x": 4, "y": 5, "type": 3 }
    ]
}}
```
