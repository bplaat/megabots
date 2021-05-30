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

## Protocol:
All message are encoded in JSON and send over an plain WebSocket connection with the centeral websockets server.

```
> robot 1 { robot_connect }
< robot 1 { world_info }
< robot 2 { robot_connect }
< robot 3 { robot_connect }
< robot 4 { robot_connect }

> website { new_direction or cancel_direction }
< robot 1 { new_direction or cancel_direction }
< robot 2 { new_direction or cancel_direction }
< robot 3 { new_direction or cancel_direction }
< robot 4 { new_direction or cancel_direction }

loop {
    < robot 1 { robot_tick }

    > robot 1 { robot_tick_done }
    < robot 2 { robot_tick_done }
    < robot 3 { robot_tick_done }
    < robot 4 { robot_tick_done }
}

**Robot 1 disconnects**
< robot 2 { robot_disconnect }
< robot 3 { robot_disconnect }
< robot 4 { robot_disconnect }
```

### Robot connect message
```json
{
    "type": "robot_connect",
    "data": {
        "robot_id": 1,
        "robot_x": 3,
        "robot_y": 3,
        "robot_lift": 200,
        "directions": [
            {
                "id": 1621529804034,
                "x": 4,
                "y": 5
            },
            {
                "id": 1621529804035,
                "x": 1,
                "y": 1
            }
        ]
    }
}
```

### Robot disconnect message
```json
{ "type": "robot_disconnect", "data": { "robot_id": 1 } }
```

### Website connect message
```json
{ "type": "website_connect", "data": { "website_id": 1621576963658 } }
```

### Website disconnect message
```json
{ "type": "website_disconnect", "data": { "website_id": 1621576963658 } }
```

### World info message
```python
TICK_MANUAL = 0
TICK_AUTO = 1
```

```json
{
    "type": "world_info",
    "data": {
        "tick_type": 0,
        "tick_speed": 500,
        "map": {
            "width": 16,
            "height": 16,
            "data": [ 1, 1, 2... ]
        }
    }
}
```

### Update world info message
```json
{
    "type": "update_world_info",
    "data": {
        "tick_type": 1,
        "tick_speed": 500
    }
}
```

### New direction message
```json
{
    "type": "new_direction",
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

### World (manual) tick message
```json
{ "type": "world_tick", "data": {} }
```

### Robot tick message
```json
{ "type": "robot_tick", "data": {} }
```

### Robot tick done message
```python
TILE_UNKOWN = 0
TILE_FLOOR = 1
TILE_CHEST = 2
```
```json
{
    "type": "robot_tick_done",
    "data": {
        "robot_id": 1,
        "robot_x":  4,
        "robot_y":  4,
        "map": [
            { "x": 3, "y": 4, "type": 1 },
            { "x": 5, "y": 4, "type": 2 },
            { "x": 4, "y": 3, "type": 1 },
            { "x": 4, "y": 5, "type": 2 }
        ]
    }
}
```

### Website tick message
```json
{ "type": "website_tick", "data": {} }
```
