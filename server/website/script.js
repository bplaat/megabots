// Constants
const WEBSOCKETS_PORT = 8082;

const MAP_WIDTH = 12;
const MAP_HEIGHT = 12;
const TILE_UNKOWN = 0;
const TILE_NORMAL = 1;
const TILE_WALL = 2;

// App
const app = new Vue({
    el: '#app',

    data: {
        connected: false,

        robots: [
            { id: 1, x: 1, y: 1, directions: [], connected: false },
            { id: 2, x: MAP_WIDTH - 2, y: 1, directions: [], connected: false },
            { id: 3, x: 1, y: MAP_HEIGHT - 2, directions: [], connected: false },
            { id: 4, x: MAP_WIDTH - 2, y: MAP_HEIGHT - 2, directions: [], connected: false }
        ]
    },

    methods: {
        websocketsConnect() {
            const ws = new WebSocket("ws://127.0.0.1:" + WEBSOCKETS_PORT + "/");

            ws.onopen = () => {
                this.connected = true;
            };

            ws.onmessage = event => {
                console.log('Server message:', event.data);
                const message = JSON.parse(event.data);

                if (message.type == 'connect') {
                    const robot = this.robots.find(robot => robot.id == message.data.id);
                    robot.connected = true;
                }

                if (message.type == 'disconnect') {
                    const robot = this.robots.find(robot => robot.id == message.data.id);
                    robot.connected = false;
                }
            };

            ws.onclose = () => {
                this.connected = false;
            };
        }
    },

    created() {
        this.websocketsConnect();
    }
})
