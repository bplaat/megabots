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
> robot 1 { connect }
< robot 2 { connect }
< robot 3 { connect }
< robot 4 { connect }

> robot 2 { new_direction or update_direction or cancel_direction }
< robot 1 { new_direction or update_direction or cancel_direction }
< robot 3 { new_direction or update_direction or cancel_direction }
< robot 4 { new_direction or update_direction or cancel_direction }

loop {
    < robot 1 { tick with robot_id = 1 }
    < robot 2 { tick with robot_id = 1 }
    < robot 3 { tick with robot_id = 1 }
    < robot 4 { tick with robot_id = 1 }

    > robot 1 { tick_done }
    < robot 2 { tick_done }
    < robot 3 { tick_done }
    < robot 4 { tick_done }
}

**Robot 1 disconnects**
< robot 2 { disconnect }
< robot 3 { disconnect }
< robot 4 { disconnect }
```

### Connect message
```json
{ "type": "connect", "data": { "robot_id": 1 } }
```

### Disconnect message
```json
{ "type": "disconnect", "data": { "robot_id": 1 } }
```

### Start message
```json
{ "type": "start", "data": {} }
```

### Stop message
```json
{ "type": "stop", "data": {} }
```

### New direction message
```json
{
    "type": "new_direction",
    "data": {
        "robot_id": 1,
        "direction": {
            "id": 1621529804034, // time in ms (for random id)
            "x": 4,
            "y": 5
        }
    }
}
```

### Update direction message
```json
{
    "type": "update_direction",
    "data": {
        "robot_id": 1,
        "direction": {
            "id": 1621529804034,
            "x": 4,
            "y": 5
        }
    }
}
```

### Cancel direction message
```json
{
    "type": "cancel_direction",
    "data": {
        "robot_id": 1,
        "direction": {
            "id": 1621529804034
        }
    }
}
```

### Tick message
```json
{ "type": "tick", "data": { "robot_id": 1 } }
```

### Tick done message
Robot 1 -> Server
```python
TILE_UNKOWN = 0
TILE_NORMAL = 1
TILE_CHEST = 2
TILE_WALL = 3
```
```json
{
    "type": "tick_done",
    "data": {
        "robot_id": 1,
        "robot_x":  4,
        "robot_y":  4,
        "map": [
            { "x": 3, "y": 4, "type": 1 },
            { "x": 5, "y": 4, "type": 3 },
            { "x": 4, "y": 3, "type": 1 },
            { "x": 4, "y": 5, "type": 3 }
        ]
    }
}
```

### Tick done message
Server -> Other robots
```json
{
    "type": "tick_done",
    "data": {
        "robot_id": 1,
        "robot_x":  4,
        "robot_y":  4,
        "map": [
            { "x": 3, "y": 4, "type": 1 },
            { "x": 5, "y": 4, "type": 3 },
            { "x": 4, "y": 3, "type": 1 },
            { "x": 4, "y": 5, "type": 3 }
        ]
    }
}
```
