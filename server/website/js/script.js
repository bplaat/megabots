// Constants
const WEBSOCKETS_PORT = 8082;

const MAP_WIDTH = 12;
const MAP_HEIGHT = 12;
const TILE_UNKOWN = 0;
const TILE_NORMAL = 1;
const TILE_CHEST = 2;
const TILE_WALL = 3;

const map = new Array(MAP_HEIGHT * MAP_WIDTH);
for (let y = 0; y < MAP_HEIGHT; y++) {
    for (let x = 0; x < MAP_WIDTH; x++) {
        if (x == 0 || y == 0 || x == MAP_WIDTH - 1 || y == MAP_HEIGHT - 1) {
            map[y * MAP_WIDTH + x] = TILE_WALL;
        } else if (
            (x == 1 && y == 1) ||
            (x == MAP_WIDTH - 2 && y == 1) ||
            (x == 1 && y == MAP_HEIGHT - 2) ||
            (x == MAP_WIDTH - 2 && y == MAP_HEIGHT - 2)
        ) {
            map[y * MAP_WIDTH + x] = TILE_NORMAL;
        } else {
            map[y * MAP_WIDTH + x] = (x + y) % 3 || x == 1 || y == 1 || x == MAP_WIDTH - 2 || y == MAP_HEIGHT - 2 ? TILE_NORMAL : TILE_CHEST;
            // map[y * MAP_WIDTH + x] = TILE_UNKOWN;
        }
    }
}

// App
const app = new Vue({
    el: '#app',

    data: {
        connected: false,

        robots: [
            { id: 1, x: 1, y: 1, color: 0xff0000, directions: [], connected: false },
            { id: 2, x: MAP_WIDTH - 2, y: 1, color: 0x00ff00,directions: [], connected: false },
            { id: 3, x: 1, y: MAP_HEIGHT - 2, color: 0xffff00,directions: [], connected: false },
            { id: 4, x: MAP_WIDTH - 2, y: MAP_HEIGHT - 2, color: 0x0000ff,directions: [], connected: false }
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

        // 3D Map Simulation
        const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas') });
        renderer.setClearColor(0x87CEEB);
        renderer.setSize(1280, 720);

        const scene = new THREE.Scene();

        const camera = new THREE.PerspectiveCamera( 75, 1280 / 720, 0.1, 1000 );
        camera.position.y = MAP_WIDTH;

        const controls = new THREE.OrbitControls(camera, renderer.domElement);

        // Create map meshes
        const mapMeshes = [];

        const cubeGeometry = new THREE.BoxGeometry(1, 1, 1);
        const floorGeometry = new THREE.PlaneGeometry(1, 1);
        const unkownMaterial = new THREE.MeshBasicMaterial({ color: 0x222222, map: new THREE.TextureLoader().load('/images/unkown.jpg') });
        const floorMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/floor.jpg'), side: THREE.DoubleSide });
        const chestMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/chest.jpg') });
        const wallMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/wall.jpg') });

        for (let y = 0; y < MAP_HEIGHT; y++) {
            for (let x = 0; x < MAP_WIDTH; x++) {
                const type = map[y * MAP_WIDTH + x];

                let material;
                if (type == TILE_UNKOWN) material = unkownMaterial;
                if (type == TILE_NORMAL) material = floorMaterial;
                if (type == TILE_CHEST) material = chestMaterial;
                if (type == TILE_WALL) material = wallMaterial;

                const tileMesh = new THREE.Mesh(type == TILE_NORMAL ? floorGeometry : cubeGeometry, material);
                tileMesh.position.x = x - MAP_WIDTH / 2;
                tileMesh.position.z = y - MAP_HEIGHT / 2;
                if (type == TILE_NORMAL) tileMesh.position.y = -0.5;
                if (type == TILE_NORMAL) tileMesh.rotation.x = -Math.PI / 2;

                mapMeshes[y * MAP_WIDTH + x] = tileMesh;
                scene.add(tileMesh);
            }
        }

        // Create robot meshes
        const robotsMeshes = [];

        const robotGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.99, 32);
        const robotTexure = new THREE.TextureLoader().load('/images/robot.jpg');

        for (const robot of this.robots) {
            const robotMaterial = new THREE.MeshBasicMaterial({ color: robot.color, map: robotTexure });
            const robotMesh = new THREE.Mesh(robotGeometry, robotMaterial);
            robotMesh.position.x = robot.x - MAP_WIDTH / 2;
            robotMesh.position.z = robot.y - MAP_HEIGHT / 2;

            robotsMeshes[robot.id - 1] = robotMesh;
            scene.add(robotMesh);
        }

        // Map renderer loop
        function loop() {
            controls.update();
            renderer.render(scene, camera);
            window.requestAnimationFrame(loop);
        }
        loop();
    }
});
