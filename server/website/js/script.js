// Constants
const DEBUG = true;

const WEBSOCKETS_PORT = 8080;

const TICK_MANUAL = 0;
const TICK_AUTO = 1;

const TILE_UNKOWN = 0;
const TILE_FLOOR = 1;
const TILE_CHEST = 2;
const TILE_WALL = 3;

// App
let websocket, mapMeshesGroup, floorGeometry, cubeGeometry, wallGeometry,unkownMaterial, floorMaterial, chestMaterial, wallMaterial;
const mapMeshes = [], robotsGroups = [];

function rand (min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

const app = new Vue({
    el: '#app',

    data: {
        tickManual: TICK_MANUAL,
        tickAuto: TICK_AUTO,

        id: Date.now(),
        connected: false,
        tickType: undefined,
        tickSpeed: undefined,

        mapWidth: undefined,
        mapHeight: undefined,
        mapData: [],

        robots: [
            { id: 1, color: 0xff0000, x: undefined, y: undefined, directions: [], connected: false },
            { id: 2, color: 0x00ff00, x: undefined, y: undefined, directions: [], connected: false },
            { id: 3, color: 0xffff00, x: undefined, y: undefined, directions: [], connected: false },
            { id: 4, color: 0x0000ff, x: undefined, y: undefined, directions: [], connected: false }
        ],

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
        },

        activeProgram: 'Discover',
        programs: {
            Nothing() {},
            Discover() {
                // Check if there are unkown tiles
                let isDiscovered = true;
                for (let i = 0; i < this.mapHeight * this.mapWidth; i++) {
                    if (this.mapData[i] == TILE_UNKOWN) {
                        isDiscovered = false;
                        break;
                    }
                }

                if (!isDiscovered) {
                    // Get list off all unkown tiles
                    let unkownTiles = [];
                    for (let y = 0; y < this.mapHeight; y++) {
                        for (let x = 0; x < this.mapWidth; x++) {
                            if (this.mapData[y * this.mapWidth + x] == TILE_UNKOWN) {
                                unkownTiles.push({ x: x, y: y });
                            }
                        }
                    }

                    for (const robot of this.robots) {
                        if (robot.directions.length == 0 && unkownTiles.length > 0) {
                            // Get closest unkown tile
                            let closestUnkownTile = unkownTiles[0];
                            for (const unkownTile of unkownTiles) {
                                if (
                                    Math.sqrt((unkownTile.x - robot.x) ** 2 + (unkownTile.y - robot.y) ** 2) <
                                    Math.sqrt((closestUnkownTile.x - robot.x) ** 2 + (closestUnkownTile.y - robot.y) ** 2)
                                ) {
                                    closestUnkownTile = unkownTile;
                                }
                            }

                            // Drive robot to closest unkown tile
                            websocket.send(JSON.stringify({
                                type: 'new_direction',
                                data: {
                                    robot_id: robot.id,
                                    direction: {
                                        id: Date.now(),
                                        x: closestUnkownTile.x,
                                        y: closestUnkownTile.y
                                    }
                                }
                            }));

                            // Remove tile from list
                            unkownTiles = unkownTiles.filter(tile => !(tile.x == closestUnkownTile.x && tile.y == closestUnkownTile.y));
                        }
                    }
                }
            },
            Random() {
                for (const robot of this.robots) {
                    if (robot.directions.length == 0) {
                        // Drive robot to closest unkown tile
                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: Date.now(),
                                    x: rand(1, this.mapWidth - 2),
                                    y: rand(1, this.mapHeight - 2)
                                }
                            }
                        }));
                    }
                }
            }
        }
    },

    watch: {
        tickType(tickType, oldTickType) {
            if (this.connected && tickType != oldTickType) {
                websocket.send(JSON.stringify({
                    type: 'update_world_info',
                    data: {
                        tick_type: tickType
                    }
                }));
            }
        },

        tickSpeed(tickSpeed, oldTickSpeed) {
            if (this.connected && tickSpeed != oldTickSpeed) {
                websocket.send(JSON.stringify({
                    type: 'update_world_info',
                    data: {
                        tick_speed: tickSpeed
                    }
                }));
            }
        }
    },

    methods: {
        websocketsConnect() {
            websocket = new WebSocket('ws://127.0.0.1:' + WEBSOCKETS_PORT + '/');

            websocket.onopen = () => {
                websocket.send(JSON.stringify({
                    type: 'website_connect',
                    data: {
                        website_id: this.id
                    }
                }));
                this.connected = true;
            };

            websocket.onmessage = event => {
                if (DEBUG) {
                    console.log('Server message: ' + event.data);
                }
                const message = JSON.parse(event.data);

                // Connect message
                if (message.type == 'robot_connect') {
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
                if (message.type == 'robot_disconnect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.connected = false;

                    if (robotsGroups.length > 0) {
                        robotsGroups[robot.id - 1].visible = false;
                    }
                }

                // World info message
                if (message.type == 'world_info') {
                    this.tickType = message.data.tick_type;
                    this.tickSpeed = message.data.tick_speed;

                    this.mapWidth = message.data.map.width;
                    this.mapHeight = message.data.map.height;
                    for (let y = 0; y < this.mapHeight; y++) {
                        for (let x = 0; x < this.mapWidth; x++) {
                            this.mapData[y * this.mapWidth + x] = message.data.map.data[y * this.mapWidth + x];
                        }
                    }

                    this.startWorldSimulation();
                }

                // Update world info message
                if (message.type == 'update_world_info') {
                    if (message.data.tick_type != undefined) {
                        this.tickType = message.data.tick_type;
                    }
                    if (message.data.tick_speed != undefined) {
                        this.tickSpeed = message.data.tick_speed;
                    }
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
                if (message.type == 'robot_tick_done') {
                    for (const mapUpdate of message.data.map) {
                        this.worldUpdateTile(mapUpdate.x, mapUpdate.y, mapUpdate.type);
                    }

                    this.worldMoveRobot(message.data.robot_id, message.data.robot_x, message.data.robot_y);
                }

                // Website tick message
                if (message.type == 'website_tick') {
                    this.programs[this.activeProgram].bind(this)();
                }
            };

            websocket.onclose = () => {
                this.connected = false;
            };
        },

        cancelDirection(robotId, directionId) {
            if (websocket != undefined) {
                websocket.send(JSON.stringify({
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
            if (this.tickType == TICK_MANUAL) {
                websocket.send(JSON.stringify({
                    type: 'world_tick',
                    data: {}
                }));
            }
        },

        sendFormSubmit() {
            if (websocket != undefined) {
                websocket.send(JSON.stringify({
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
            if (websocket != undefined) {
                const directionId = Date.now();

                websocket.send(JSON.stringify({
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

                websocket.send(JSON.stringify({
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
            if (type != this.mapData[y * this.mapWidth + x]) {
                this.mapData[y * this.mapWidth + x] = type;

                if (mapMeshes.length > 0) {
                    mapMeshesGroup.remove(mapMeshes[y * this.mapWidth + x]);

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;
                    if (type == TILE_WALL) geometry = wallGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;
                    if (type == TILE_WALL) material = wallMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;
                    if (type == TILE_WALL) tileMesh.position.y = 0.25;

                    mapMeshes[y * this.mapWidth + x] = tileMesh;
                    mapMeshesGroup.add(tileMesh);
                }
            }
        },

        worldMoveRobot(robotId, x, y) {
            const robot = this.robots.find(robot => robot.id == robotId);

            if (robotsGroups.length > 0) {
                if (robotsGroups[robot.id - 1].visible) {
                    const coords = { x: robot.x, y: robot.y }
                    const tween = new TWEEN.Tween(coords)
                        .to({ x: x, y: y}, this.tickSpeed)
                        .easing(TWEEN.Easing.Quadratic.Out)
                        .onUpdate(() => {
                            robotsGroups[robot.id - 1].position.x = coords.x - this.mapWidth / 2;
                            robotsGroups[robot.id - 1].position.z = coords.y - this.mapHeight / 2;
                        })
                        .start();
                } else {
                    robotsGroups[robot.id - 1].position.x = x - this.mapWidth / 2;
                    robotsGroups[robot.id - 1].position.z = y - this.mapHeight / 2;
                }

                robotsGroups[robot.id - 1].visible = true;
            }

            robot.x = x;
            robot.y = y;
        },

        startWorldSimulation() {
            // 3D Map Simulation
            const scene = new THREE.Scene();

            const camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 0.1, 1000 );
            camera.position.y = this.mapWidth;

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

            floorGeometry = new THREE.PlaneGeometry(1, 1);
            cubeGeometry = new THREE.BoxGeometry(1, 1, 1);
            wallGeometry = new THREE.BoxGeometry(1, 1.5, 1);
            unkownMaterial = new THREE.MeshBasicMaterial({ color: 0x222222, map: new THREE.TextureLoader().load('/images/unkown.jpg') });
            floorMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/floor.jpg'), side: THREE.DoubleSide });
            chestMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/chest.jpg') });
            wallMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/wall.jpg') });

            for (let y = 0; y < this.mapHeight; y++) {
                for (let x = 0; x < this.mapWidth; x++) {
                    const type = this.mapData[y * this.mapWidth + x];

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;
                    if (type == TILE_WALL) geometry = wallGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;
                    if (type == TILE_WALL) material = wallMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;
                    if (type == TILE_WALL) tileMesh.position.y = 0.25;

                    mapMeshes[y * this.mapWidth + x] = tileMesh;
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
                    robotGroup.position.x = robot.x - this.mapWidth / 2;
                    robotGroup.position.z = robot.y - this.mapHeight / 2;
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
            function loop(delta) {
                stats.begin();
                controls.update();
                TWEEN.update(delta)
                renderer.render(scene, camera);
                stats.end();
                window.requestAnimationFrame(loop);
            }
            window.requestAnimationFrame(loop);
        }
    },

    created() {
        this.websocketsConnect();
    }
});
