# Simple event communication system between client (connection) and (webots) controller
listeners = []

def on(type, callback):
    listeners.append({ "type": type, "once": False, "callback": callback })

def once(type, callback):
    listeners.append({ "type": type, "once": True, "callback": callback })

def off(type, callback):
    global listeners
    listeners = [listener for listener in listeners if not (listener["type"] == type and listener["callback"] == callback)]

async def send(type, data = {}):
    global listeners
    newListeners = []
    for listener in listeners:
        if listener["type"] == type:
            await listener["callback"](data)
            if not listener["once"]:
                newListeners.append(listener)
        else:
            newListeners.append(listener)
    listeners = newListeners
