// Constants
const WEBSOCKETS_PORT = 8080;

const TICK_AUTO = 0;
const TICK_MANUAL = 1;

const MAP_WIDTH = 16;
const MAP_HEIGHT = 16;

const TILE_UNKOWN = 0;
const TILE_FLOOR = 1;
const TILE_CHEST = 2;
const TILE_WALL = 3;

// Map
const map = new Array(MAP_HEIGHT * MAP_WIDTH);
for (let y = 0; y < MAP_HEIGHT; y++) {
    for (let x = 0; x < MAP_WIDTH; x++) {
        if (x == 0 || y == 0 || x == MAP_WIDTH - 1 || y == MAP_HEIGHT - 1) {
            map[y * MAP_WIDTH + x] = TILE_WALL;
        } else {
            map[y * MAP_WIDTH + x] = TILE_UNKOWN;
        }
    }
}

// App
let ws, mapMeshesGroup, cubeGeometry, floorGeometry, unkownMaterial, floorMaterial, chestMaterial, wallMaterial;
const mapMeshes = [], robotsGroups = [];
const app = new Vue({
    el: '#app',

    data: {
        tickAuto: TICK_AUTO,
        tickManual: TICK_MANUAL,
        mapWidth: MAP_WIDTH,
        mapHeight: MAP_HEIGHT,

        robots: [
            { id: 1, color: 0xff0000, x: undefined, y: undefined, directions: [], connected: false },
            { id: 2, color: 0x00ff00, x: undefined, y: undefined, directions: [], connected: false },
            { id: 3, color: 0xffff00, x: undefined, y: undefined, directions: [], connected: false },
            { id: 4, color: 0x0000ff, x: undefined, y: undefined, directions: [], connected: false }
        ],

        id: Date.now(),
        connected: false,
        running: true,
        tickType: TICK_AUTO,
        tickSpeed: 500,

        sendForm: {
            robot_id: 1,
            robot_x: 1,
            robot_y: 1
        },

        pickupForm: {
            robot_id: 1,
            robot_x1: 1,
            robot_y1: 1,
            robot_x2: 2,
            robot_y2: 2
        }
    },

    watch: {
        running(running, oldRunning) {
            if (this.connected && running != oldRunning) {
                if (running) {
                    ws.send(JSON.stringify({
                        type: 'start',
                        data: {}
                    }));
                } else {
                    ws.send(JSON.stringify({
                        type: 'stop',
                        data: {}
                    }));
                }
            }
        }
    },

    methods: {
        websocketsConnect() {
            ws = new WebSocket("ws://127.0.0.1:" + WEBSOCKETS_PORT + "/");

            ws.onopen = () => {
                ws.send(JSON.stringify({
                    type: 'website_connect',
                    data: {
                        website_id: this.id
                    }
                }));
                this.connected = true;
            };

            ws.onmessage = event => {
                console.log('Server message:', event.data);
                const message = JSON.parse(event.data);

                // Connect message
                if (message.type == 'connect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    this.worldUpdateTile(message.data.robot_x, message.data.robot_y, TILE_FLOOR);
                    this.worldMoveRobot(robot.id, message.data.robot_x, message.data.robot_y);

                    robot.directions = [];
                    for (const direction of message.data.directions) {
                        robot.directions.push({
                            id: direction.id,
                            x: direction.x,
                            y: direction.y
                        })
                    }

                    robot.connected = true;
                }

                // Disconnect message
                if (message.type == 'disconnect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.connected = false;

                    if (robotsGroups.length > 0) {
                        robotsGroups[robot.id - 1].visible = false;
                    }
                }

                // Start message
                if (message.type == 'start') {
                    this.running = true;
                }

                // Stop message
                if (message.type == 'stop') {
                    this.running = false;
                }

                // New direction message
                if (message.type == 'new_direction') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.directions.push({
                        id: message.data.direction.id,
                        x: message.data.direction.x,
                        y: message.data.direction.y
                    });
                }

                // Cancel direction message
                if (message.type == 'cancel_direction') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.directions = robot.directions.filter(direction => direction.id != message.data.direction.id);
                }

                // Tick done message
                if (message.type == 'tick_done') {
                    for (const mapUpdate of message.data.map) {
                        this.worldUpdateTile(mapUpdate.x, mapUpdate.y, mapUpdate.type);
                    }
                    this.worldMoveRobot(message.data.robot_id, message.data.robot_x, message.data.robot_y);
                }
            };

            ws.onclose = () => {
                this.connected = false;
            };
        },

        cancelDirection(robotId, directionId) {
            if (ws != undefined) {
                ws.send(JSON.stringify({
                    type: 'cancel_direction',
                    data: {
                        robot_id: robotId,
                        direction: {
                            id: directionId
                        }
                    }
                }));
            }
        },

        tick() {
            // TODO
        },

        sendFormSubmit() {
            if (ws != undefined) {
                ws.send(JSON.stringify({
                    type: 'new_direction',
                    data: {
                        robot_id: this.sendForm.robot_id,
                        direction: {
                            id: Date.now(),
                            x: this.sendForm.robot_x,
                            y: this.sendForm.robot_y
                        }
                    }
                }));
            }
        },

        pickupFormSubmit() {
            if (ws != undefined) {
                const directionId = Date.now();

                ws.send(JSON.stringify({
                    type: 'new_direction',
                    data: {
                        robot_id: this.pickupForm.robot_id,
                        direction: {
                            id: directionId,
                            x: this.pickupForm.robot_x1,
                            y: this.pickupForm.robot_y1
                        }
                    }
                }));

                ws.send(JSON.stringify({
                    type: 'new_direction',
                    data: {
                        robot_id: this.pickupForm.robot_id,
                        direction: {
                            id: directionId + 1,
                            x: this.pickupForm.robot_x2,
                            y: this.pickupForm.robot_y2
                        }
                    }
                }));
            }
        },

        worldUpdateTile(x, y, type) {
            map[y * MAP_WIDTH + x] = type;

            if (mapMeshes.length > 0) {
                mapMeshesGroup.remove(mapMeshes[y * MAP_WIDTH + x]);

                let material;
                if (type == TILE_UNKOWN) material = unkownMaterial;
                if (type == TILE_FLOOR) material = floorMaterial;
                if (type == TILE_CHEST) material = chestMaterial;
                if (type == TILE_WALL) material = wallMaterial;

                const tileMesh = new THREE.Mesh(type == TILE_FLOOR ? floorGeometry : cubeGeometry, material);
                tileMesh.position.x = x - MAP_WIDTH / 2;
                tileMesh.position.z = y - MAP_HEIGHT / 2;
                if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;

                mapMeshes[y * MAP_WIDTH + x] = tileMesh;
                mapMeshesGroup.add(tileMesh);
            }
        },

        worldMoveRobot(robotId, x, y) {
            const robot = this.robots.find(robot => robot.id == robotId);
            robot.x =x;
            robot.y = y;

            if (robotsGroups.length > 0) {
                robotsGroups[robot.id - 1].visible = true;
                robotsGroups[robot.id - 1].position.x = x - MAP_WIDTH / 2;
                robotsGroups[robot.id - 1].position.z = y - MAP_HEIGHT / 2;
            }
        },

        worldSimulation() {
            // 3D Map Simulation
            const scene = new THREE.Scene();

            const camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 0.1, 1000 );
            camera.position.y = MAP_WIDTH;

            const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas') });
            renderer.setClearColor(0x87ceeb);
            renderer.setSize(window.innerWidth, window.innerHeight);

            window.addEventListener('resize', function () {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();

                renderer.setSize(window.innerWidth, window.innerHeight);
            });

            const controls = new THREE.OrbitControls(camera, renderer.domElement);

            const stats = new Stats();
            stats.dom.style.top = '';
            stats.dom.style.left = '';
            stats.dom.style.right = '8px';
            stats.dom.style.bottom = '8px';
            document.body.appendChild(stats.dom);

            // Create map meshes
            mapMeshesGroup = new THREE.Group();
            scene.add(mapMeshesGroup);

            cubeGeometry = new THREE.BoxGeometry(1, 1, 1);
            floorGeometry = new THREE.PlaneGeometry(1, 1);
            unkownMaterial = new THREE.MeshBasicMaterial({ color: 0x222222, map: new THREE.TextureLoader().load('/images/unkown.jpg') });
            floorMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/floor.jpg'), side: THREE.DoubleSide });
            chestMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/chest.jpg') });
            wallMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/wall.jpg') });

            for (let y = 0; y < MAP_HEIGHT; y++) {
                for (let x = 0; x < MAP_WIDTH; x++) {
                    const type = map[y * MAP_WIDTH + x];

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;
                    if (type == TILE_WALL) material = wallMaterial;

                    const tileMesh = new THREE.Mesh(type == TILE_FLOOR ? floorGeometry : cubeGeometry, material);
                    tileMesh.position.x = x - MAP_WIDTH / 2;
                    tileMesh.position.z = y - MAP_HEIGHT / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;

                    mapMeshes[y * MAP_WIDTH + x] = tileMesh;
                    mapMeshesGroup.add(tileMesh);
                }
            }

            // Create robot meshes
            const robotGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.999, 32);
            const robotTexure = new THREE.TextureLoader().load('/images/robot.jpg');
            const sensorGeometry = new THREE.SphereGeometry(0.05, 32, 32);

            for (const robot of this.robots) {
                const robotGroup = new THREE.Group();
                if (robot.x != undefined && robot.y != undefined) {
                    robotGroup.position.x = robot.x - MAP_WIDTH / 2;
                    robotGroup.position.z = robot.y - MAP_HEIGHT / 2;
                } else {
                    robotGroup.visible = false;
                }
                scene.add(robotGroup);
                robotsGroups[robot.id - 1] = robotGroup;

                const robotMaterial = new THREE.MeshBasicMaterial({ color: robot.color, map: robotTexure });
                robotGroup.add(new THREE.Mesh(robotGeometry, robotMaterial));

                const sensorMaterial = new THREE.MeshBasicMaterial({ color: robot.color });

                const sensorMesh1 = new THREE.Mesh(sensorGeometry, sensorMaterial);
                sensorMesh1.position.x = -0.3;
                robotGroup.add(sensorMesh1);

                const sensorMesh2 = new THREE.Mesh(sensorGeometry, sensorMaterial);
                sensorMesh2.position.x = 0.3;
                robotGroup.add(sensorMesh2);

                const sensorMesh3 = new THREE.Mesh(sensorGeometry, sensorMaterial);
                sensorMesh3.position.z = -0.3;
                robotGroup.add(sensorMesh3);

                const sensorMesh4 = new THREE.Mesh(sensorGeometry, sensorMaterial);
                sensorMesh4.position.z = 0.3;
                robotGroup.add(sensorMesh4);
            }

            // Map renderer loop
            function loop() {
                stats.begin();
                controls.update();
                renderer.render(scene, camera);
                stats.end();
                window.requestAnimationFrame(loop);
            }
            loop();
        }
    },

    created() {
        this.websocketsConnect();
        this.worldSimulation();
    }
});
