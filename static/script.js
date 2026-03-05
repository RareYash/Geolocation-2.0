/**
 * Geo-loc — Frontend Logic (Dribbble Layout)
 */

let map = null;
let markersLayer = null;
let selectedCategories = new Set();
let currentResults = {};
let userLat = null;
let userLng = null;
let categoriesData = {};

const MARKER_COLORS = {
    restaurant: '#ef4444',
    grocery: '#10b981',
    bus_stop: '#3b82f6',
    train_station: '#8b5cf6',
    medical: '#14b8a6',
    gym: '#f97316',
    atm_bank: '#06b6d4',
    study_space: '#22d3ee',
};

document.addEventListener('DOMContentLoaded', () => {
    initMap(19.9975, 73.7898); // Default Nashik center
    loadCategories();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('searchForm').addEventListener('submit', handleSearch);
    document.getElementById('detectLocationBtn').addEventListener('click', detectLocation);

    document.getElementById('selectAllBtn').addEventListener('click', () => {
        document.querySelectorAll('.pill').forEach(c => {
            c.classList.add('selected');
            selectedCategories.add(c.dataset.id);
        });
    });

    // View Switching
    document.getElementById('backToSearchBtn').addEventListener('click', () => {
        switchView('searchView');
    });

    // Detail Overlay
    document.getElementById('closeDetailBtn').addEventListener('click', () => {
        document.getElementById('detailOverlay').classList.remove('active');
    });

    // Map Fullscreen toggle (optional visual enhancement)
    const appContainer = document.querySelector('.app-container');
    document.getElementById('fullScreenMapBtn').addEventListener('click', () => {
        appContainer.classList.toggle('map-fullscreen');
        if (appContainer.classList.contains('map-fullscreen')) {
            appContainer.style.width = '100vw';
            appContainer.style.height = '100vh';
            appContainer.style.maxWidth = '100vw';
            appContainer.style.borderRadius = '0';
        } else {
            appContainer.style.width = '96vw';
            appContainer.style.height = '92vh';
            appContainer.style.maxWidth = '1500px';
            appContainer.style.borderRadius = '40px';
        }
        setTimeout(() => map.invalidateSize(), 300);
    });

    // Generic Custom Dropdown Logic
    function initCustomDropdown(dropdownId, inputId) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;

        const btn = dropdown.querySelector('.custom-dropdown-btn');
        const label = dropdown.querySelector('span'); // usually the first span holds the label
        const input = document.getElementById(inputId);
        const options = dropdown.querySelectorAll('.custom-option');

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close others
            document.querySelectorAll('.custom-dropdown-container.open').forEach(d => {
                if (d !== dropdown) d.classList.remove('open');
            });
            dropdown.classList.toggle('open');
        });

        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                // Update UI visually
                options.forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');

                // Extra logic specific to City Dropdown
                if (dropdownId === 'cityDropdown') {
                    label.textContent = option.textContent;
                    const coords = option.dataset.value.split(',');
                    const lat = parseFloat(coords[0]);
                    const lng = parseFloat(coords[1]);

                    if (map) map.setView([lat, lng], 13);
                    userLat = lat; userLng = lng;

                    const cityName = option.dataset.name || "Selected Area";
                    document.getElementById('locationInput').value = `${cityName}, Maharashtra`;
                } else {
                    // Normal Dropdowns just update label directly to data-label
                    label.textContent = option.dataset.label;
                }

                // Update hidden input
                if (input) {
                    input.value = option.dataset.value;
                }

                dropdown.classList.remove('open');
            });
        });
    }

    // Initialize all custom dropdowns
    initCustomDropdown('cityDropdown', 'citySelect');
    initCustomDropdown('budgetDropdown', 'budgetSelect');
    initCustomDropdown('radiusDropdown', 'radiusSelect');

    // Global click handler to close any open dropdowns
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.custom-dropdown-container')) {
            document.querySelectorAll('.custom-dropdown-container').forEach(d => d.classList.remove('open'));
        }
    });
}

function switchView(viewId) {
    document.querySelectorAll('.view-state').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    document.getElementById('detailOverlay').classList.remove('active');
}

// ── Categories ──
async function loadCategories() {
    try {
        const resp = await fetch('/api/categories');
        const data = await resp.json();
        const grid = document.getElementById('categoryGrid');
        grid.innerHTML = '';

        data.categories.forEach(cat => {
            categoriesData[cat.id] = cat;
            const pill = document.createElement('div');
            pill.className = 'pill';
            pill.dataset.id = cat.id;
            pill.innerHTML = `<span style="font-size:18px">${cat.icon}</span> ${cat.label}`;

            pill.addEventListener('click', () => {
                pill.classList.toggle('selected');
                if (selectedCategories.has(cat.id)) selectedCategories.delete(cat.id);
                else selectedCategories.add(cat.id);
            });
            grid.appendChild(pill);
        });
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

// ── Location ──
function detectLocation() {
    const btn = document.getElementById('detectLocationBtn');
    btn.innerHTML = `<svg width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg> Locating...`;

    if (!navigator.geolocation) {
        showError('Geolocation not supported.');
        btn.innerHTML = `Detect`; return;
    }

    navigator.geolocation.getCurrentPosition(
        async pos => {
            userLat = pos.coords.latitude;
            userLng = pos.coords.longitude;

            try {
                const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${userLat}&lon=${userLng}&format=json`);
                const data = await resp.json();
                document.getElementById('locationInput').value = data.display_name || `${userLat.toFixed(4)}, ${userLng.toFixed(4)}`;
            } catch {
                document.getElementById('locationInput').value = `${userLat.toFixed(4)}, ${userLng.toFixed(4)}`;
            }

            btn.innerHTML = `✓ Located`;
        },
        () => {
            showError('Could not detect location.');
            btn.innerHTML = `Detect`;
        },
        { enableHighAccuracy: true, timeout: 5000 }
    );
}

// ── Search ──
function showError(msg) {
    const err = document.getElementById('formError');
    err.textContent = msg;
    err.style.display = 'block';
    setTimeout(() => err.style.display = 'none', 4000);
}

async function handleSearch(e) {
    e.preventDefault();
    if (selectedCategories.size === 0) { showError('Select at least one category.'); return; }
    const locationInput = document.getElementById('locationInput').value.trim();
    if (!locationInput) { showError('Enter your location.'); return; }

    const btn = document.getElementById('submitBtn');
    const ogText = btn.textContent;
    btn.textContent = 'Searching...';
    btn.disabled = true;

    try {
        if (!userLat || !userLng) {
            const geoResp = await fetch(`/api/geocode?q=${encodeURIComponent(locationInput)}`);
            const geoData = await geoResp.json();
            if (geoData.error) throw new Error('Location not found');
            userLat = geoData.lat;
            userLng = geoData.lng;
        }

        const budget = document.getElementById('budgetSelect').value;
        const radius = document.getElementById('radiusSelect').value;

        const resp = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userLat, lng: userLng,
                categories: Array.from(selectedCategories),
                budget: budget ? parseInt(budget) : null,
                radius: parseInt(radius)
            }),
        });

        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        updateMap(userLat, userLng, data.results);
        renderResults(data.results, data.summary);
        switchView('resultsView');

    } catch (err) {
        showError(err.message || 'Search failed.');
    } finally {
        btn.textContent = ogText;
        btn.disabled = false;
    }
}

// ── Map ──
function initMap(lat, lng) {
    map = L.map('map', { zoomControl: false }).setView([lat, lng], 13);

    // Light minimalist map tiles (CartoDB Positron) for that Dribbble look
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
}

function updateMap(lat, lng, results) {
    markersLayer.clearLayers();

    // User Location Pin (Indigo)
    const userIcon = L.divIcon({
        className: 'user-marker',
        html: `<div style="width:24px;height:24px;background:var(--grad-primary);border:4px solid white;border-radius:50%;box-shadow:0 10px 15px -3px rgba(139,92,246,0.5)"></div>`,
        iconSize: [24, 24], iconAnchor: [12, 12]
    });
    L.marker([lat, lng], { icon: userIcon, zIndexOffset: 1000 }).addTo(markersLayer);

    const bounds = L.latLngBounds([[lat, lng]]);

    // Results Pins
    for (const [catKey, places] of Object.entries(results)) {
        if (!Array.isArray(places)) continue;
        const color = MARKER_COLORS[catKey] || '#6b7280';
        const iconSymbol = categoriesData[catKey]?.icon || '📍';

        places.forEach(place => {
            if (!place.lat || !place.lng) return;

            const icon = L.divIcon({
                className: 'place-marker',
                html: `
                <div style="background:${color}; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-size:14px; border:3px solid white; box-shadow:0 8px 15px -3px rgba(0,0,0,0.15)">
                    ${iconSymbol}
                </div>`,
                iconSize: [32, 32], iconAnchor: [16, 16]
            });

            L.marker([place.lat, place.lng], { icon })
                .bindPopup(`<b>${place.name}</b><br>${place.distance_m}m away`)
                .addTo(markersLayer)
                .on('click', () => openDetail(place.osm_type, place.place_id));

            bounds.extend([place.lat, place.lng]);
        });
    }

    map.fitBounds(bounds, { padding: [50, 50] });
}

// ── Results Render ──
function renderResults(results, summary) {
    document.getElementById('resultsSummaryText').textContent =
        `Found ${summary.total_places_found} places across ${Object.keys(summary.category_counts).length} categories`;

    const container = document.getElementById('resultsContainer');
    container.innerHTML = '';

    for (const [catKey, places] of Object.entries(results)) {
        if (!places || places.length === 0) continue;
        const cat = categoriesData[catKey];

        const catTitle = document.createElement('h3');
        catTitle.style.cssText = 'font-size:1.4rem; font-weight:700; margin: 32px 0 16px; display:flex; gap:10px; align-items:center;';
        catTitle.innerHTML = `<span>${cat.icon}</span> ${cat.label} <span style="background:#f3f4f6;color:#6b7280;padding:2px 10px;border-radius:20px;font-size:0.9rem">${places.length}</span>`;
        container.appendChild(catTitle);

        places.forEach(place => {
            const card = document.createElement('div');
            card.className = 'place-card';
            card.onclick = () => openDetail(place.osm_type, place.place_id);

            const dist = place.distance_m < 1000 ? `${place.distance_m}m` : `${(place.distance_m / 1000).toFixed(1)}km`;
            const score = place.scores ? Math.round(place.scores.composite * 100) : 0;

            card.innerHTML = `
                <div class="card-top">
                    <div>
                        <div class="card-title">${place.name}</div>
                        <div class="card-address">${place.address}</div>
                    </div>
                    <div class="card-dist">${dist}</div>
                </div>
                <div class="match-bar-container">
                    <div class="match-label"><span>Match Score</span> <span style="color:#8b5cf6">${score}%</span></div>
                    <div class="m-track"><div class="m-fill" style="width:${score}%"></div></div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    if (container.children.length === 0) {
        container.innerHTML = `<div style="padding:40px;text-align:center;color:#6b7280;background:#f9fafb;border-radius:16px">No places found. Expand radius or select more categories.</div>`;
    }
}

// ── Item Detail ──
async function openDetail(osmType, placeId) {
    const overlay = document.getElementById('detailOverlay');
    const body = document.getElementById('detailBody');
    overlay.classList.add('active');

    body.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af">Loading details...</div>`;

    try {
        const resp = await fetch(`/api/place-details/${osmType}/${placeId}`);
        const data = await resp.json();

        body.innerHTML = `
            <h2 class="detail-title">${data.name}</h2>
            <p class="detail-address">📍 ${data.address}</p>
            
            <div class="detail-info">
                ${data.cuisine ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>Cuisine</b><br/>${data.cuisine}</div>` : ''}
                ${data.phone ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>📱 Contact</b><br/>${data.phone}</div>` : ''}
                ${data.hours && data.hours.length ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>🕐 Hours</b><br/>${data.hours.join('<br>')}</div>` : ''}
            </div>

            <div style="margin-top:40px;display:flex;gap:16px;">
                <a href="${data.maps_url}" target="_blank" class="btn-action" style="flex:1;">🗺️ Open in map</a>
                ${data.phone ? `<a href="tel:${data.phone}" class="btn-action" style="flex:1;background:var(--grad-primary)">📞 Call</a>` : ''}
            </div>
        `;
    } catch {
        body.innerHTML = `<div class="error-msg">Failed to load details.</div>`;
    }
}
