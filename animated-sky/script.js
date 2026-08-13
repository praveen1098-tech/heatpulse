// --- State & Setup ---
let timeOfDay = 12.0; // 0 to 24 (starts at Noon)
let isPlaying = true;
let timeSpeed = 1.0; // Hours per second (1 sec = 1 hour, ~24s cycle)
let lastTime = performance.now();

const UI_TOGGLE = document.getElementById('toggleTime');
const UI_SLIDER = document.getElementById('timeSlider');

// Interaction
UI_TOGGLE.addEventListener('click', () => {
    isPlaying = !isPlaying;
    UI_TOGGLE.textContent = isPlaying ? "Play Time" : "Pause Time";
});

UI_SLIDER.addEventListener('input', (e) => {
    timeOfDay = parseFloat(e.target.value);
    updateEnvironment(timeOfDay);
});

// --- Colors for Clouds --
const CLOUD_COLORS = {
    night: [40, 45, 65],       // Dark slate
    sunrise: [245, 170, 130],  // Soft orange/pink
    day: [255, 255, 255],      // Pure white
    sunset: [225, 135, 125]    // Dusky red/purple
};

function lerpColorArray(a, b, amount) {
    return [
        a[0] + (b[0] - a[0]) * amount,
        a[1] + (b[1] - a[1]) * amount,
        a[2] + (b[2] - a[2]) * amount
    ];
}

function rgbString(arr) {
    return `rgb(${Math.round(arr[0])}, ${Math.round(arr[1])}, ${Math.round(arr[2])})`;
}

function getCloudColor(t) {
    if (t >= 0 && t < 4) return CLOUD_COLORS.night;
    if (t >= 4 && t < 6) return lerpColorArray(CLOUD_COLORS.night, CLOUD_COLORS.sunrise, (t-4)/2);
    if (t >= 6 && t < 8) return lerpColorArray(CLOUD_COLORS.sunrise, CLOUD_COLORS.day, (t-6)/2);
    if (t >= 8 && t < 16) return CLOUD_COLORS.day;
    if (t >= 16 && t < 18) return lerpColorArray(CLOUD_COLORS.day, CLOUD_COLORS.sunset, (t-16)/2);
    if (t >= 18 && t < 20) return lerpColorArray(CLOUD_COLORS.sunset, CLOUD_COLORS.night, (t-18)/2);
    if (t >= 20 && t <= 24) return CLOUD_COLORS.night;
    return CLOUD_COLORS.night;
}

// --- Opacity Calculations for Crossfading Overlays ---
function getOpacityDay(t) {
    if (t > 7 && t < 17) return 1;
    if (t >= 5 && t <= 7) return (t - 5) / 2;
    if (t >= 17 && t <= 19) return (19 - t) / 2;
    return 0;
}
function getOpacitySunrise(t) {
    if (t > 4 && t < 8) return 1 - Math.abs(t - 6) / 2; 
    return 0;
}
function getOpacitySunset(t) {
    if (t > 16 && t < 20) return 1 - Math.abs(t - 18) / 2; 
    return 0;
}
function getOpacityNight(t) {
    if (t < 5 || t > 19) return 1;
    if (t >= 5 && t <= 7) return (7 - t) / 2;
    if (t >= 17 && t <= 19) return (t - 17) / 2;
    return 0;
}

// --- Dynamic Initialization ---
function initStars() {
    const container = document.getElementById('stars');
    for(let i=0; i<150; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        
        const size = Math.random() < 0.9 ? (Math.random() * 2 + 1) : (Math.random() * 2 + 3);
        star.style.width = size + 'px';
        star.style.height = size + 'px';
        
        star.style.left = Math.random() * 100 + 'vw';
        star.style.top = Math.random() * 65 + 'vh'; 
        
        star.style.animationDelay = Math.random() * 4 + 's';
        star.style.animationDuration = (2 + Math.random() * 3) + 's';
        
        container.appendChild(star);
    }
}

function initClouds() {
    const layers = [
        { id: 'cloudsLayer1', count: 4, duration: 80 },  // Front, fast, few
        { id: 'cloudsLayer2', count: 6, duration: 120 }, // Mid
        { id: 'cloudsLayer3', count: 10, duration: 200 } // Back, slow, many
    ];

    layers.forEach(layer => {
        const container = document.getElementById(layer.id);
        for(let i=0; i<layer.count; i++) {
            const cloud = document.createElement('div');
            cloud.className = 'cloud-base';
            
            // Proportions
            const w = 120 + Math.random() * 180;
            cloud.style.width = w + 'px';
            cloud.style.height = (w * 0.3) + 'px';
            cloud.style.top = (Math.random() * 60) + 'vh';
            
            // Build fluffy bumps
            const bumps = 2 + Math.floor(Math.random()*3);
            for(let j=0; j<bumps; j++) {
                const bump = document.createElement('div');
                bump.className = 'cloud-bump';
                const size = w * (0.35 + Math.random() * 0.35);
                bump.style.width = size + 'px';
                bump.style.height = size + 'px';
                bump.style.left = (Math.random() * (w - size)) + 'px';
                bump.style.bottom = '10%'; 
                cloud.appendChild(bump);
            }
            
            // Drift animation setup
            const delay = -Math.random() * layer.duration;
            cloud.style.animation = `drift ${layer.duration}s linear ${delay}s infinite`;
            
            container.appendChild(cloud);
        }
    });
}

// --- Main Engine Loop ---
function animate(currentTime) {
    const delta = (currentTime - lastTime) / 1000;
    lastTime = currentTime;
    
    if (isPlaying) {
        timeOfDay += delta * timeSpeed;
        if (timeOfDay >= 24) timeOfDay -= 24;
        
        // Update slider visually without triggering input event
        UI_SLIDER.value = timeOfDay;
        updateEnvironment(timeOfDay);
    }
    
    requestAnimationFrame(animate);
}

function updateEnvironment(t) {
    // 1. Move Celestial Bodies (Elliptical Arc)
    const sunAngleRads = ((t - 12) / 12) * Math.PI;
    const moonAngleRads = ((t - 0) / 12) * Math.PI;

    // Calculate dynamic radius based on window size
    const xRadius = window.innerWidth * 0.6; 
    const yRadius = window.innerHeight * 0.9;

    const sunX = Math.sin(sunAngleRads) * xRadius;
    const sunY = Math.cos(sunAngleRads) * yRadius;
    
    const moonX = Math.sin(moonAngleRads) * xRadius;
    const moonY = Math.cos(moonAngleRads) * yRadius;

    document.getElementById('sunOrbit').style.transform = `translate(${sunX}px, ${-sunY}px)`;
    document.getElementById('moonOrbit').style.transform = `translate(${moonX}px, ${-moonY}px)`;

    // 2. Crossfade Sky Backgrounds & Stars
    document.querySelector('.day-overlay').style.opacity = getOpacityDay(t);
    document.querySelector('.sunrise-overlay').style.opacity = getOpacitySunrise(t);
    document.querySelector('.sunset-overlay').style.opacity = getOpacitySunset(t);
    document.getElementById('stars').style.opacity = getOpacityNight(t);

    // 3. Update Ambient Light (Clouds)
    const cColor = getCloudColor(t);
    document.documentElement.style.setProperty('--cloud-color', rgbString(cColor));

    // 4. Toggle UI Contrast Mode
    if (t > 6 && t < 18) {
        document.body.classList.add('day-mode');
    } else {
        document.body.classList.remove('day-mode');
    }
}

// --- Run ---
initStars();
initClouds();
updateEnvironment(timeOfDay);
requestAnimationFrame(animate);

window.addEventListener('resize', () => {
    updateEnvironment(timeOfDay);
});
