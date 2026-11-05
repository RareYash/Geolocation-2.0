/**
 * Geo-loc — Frontend Logic
 */

let map = null;
let markersLayer = null;
let selectedCategories = new Set();
let currentResults = {};
let userLat = 19.9975;
let userLng = 73.7898;
let currentCityName = "Nashik";
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

// Default pre-selected categories for immediate good results
const DEFAULT_SELECTED_CATS = ['restaurant', 'grocery', 'medical', 'atm_bank'];

document.addEventListener('DOMContentLoaded', () => {
    initMap(userLat, userLng);
    setupEventListeners();
    loadCategories();
});

function setupEventListeners() {
    document.getElementById('searchForm').addEventListener('submit', handleSearch);
    document.getElementById('detectLocationBtn').addEventListener('click', detectLocation);

    // Reset coordinates if user types a custom address
    const locInput = document.getElementById('locationInput');
    if (locInput) {
        locInput.value = "Nashik, Maharashtra";
        locInput.addEventListener('input', () => {
            userLat = null;
            userLng = null;
            // Uncheck active quick city buttons
            document.querySelectorAll('.quick-city-btn').forEach(b => b.classList.remove('active'));
        });
    }

    // Select All / Deselect All Toggle
    const selectAllBtn = document.getElementById('selectAllBtn');
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            const pills = document.querySelectorAll('.pill');
            const allSelected = Array.from(pills).every(p => p.classList.contains('selected'));

            if (allSelected) {
                pills.forEach(c => {
                    c.classList.remove('selected');
                    selectedCategories.delete(c.dataset.id);
                });
                selectAllBtn.textContent = 'Select All';
            } else {
                pills.forEach(c => {
                    c.classList.add('selected');
                    selectedCategories.add(c.dataset.id);
                });
                selectAllBtn.textContent = 'Deselect All';
            }

            // If in results view, re-run search with updated categories
            if (document.getElementById('resultsView').classList.contains('active')) {
                executeSearch(false);
            }
        });
    }

    // Quick City Buttons in Left Form
    document.querySelectorAll('.quick-city-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const cityName = btn.dataset.name;
            const coords = btn.dataset.value.split(',');
            selectCity(cityName, parseFloat(coords[0]), parseFloat(coords[1]));
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

    // Map Fullscreen toggle
    const appContainer = document.querySelector('.app-container');
    const fullScreenMapBtn = document.getElementById('fullScreenMapBtn');
    if (fullScreenMapBtn) {
        fullScreenMapBtn.addEventListener('click', () => {
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
            setTimeout(() => map && map.invalidateSize(), 300);
        });
    }

    // Generic Custom Dropdowns Logic
    initCustomDropdown('cityDropdown', 'citySelect');
    initCustomDropdown('budgetDropdown', 'budgetSelect');
    initCustomDropdown('radiusDropdown', 'radiusSelect');

    // Global click handler to close dropdowns
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.custom-dropdown-container')) {
            document.querySelectorAll('.custom-dropdown-container').forEach(d => d.classList.remove('open'));
        }
    });

    // Hamburger Menu Toggle
    const hamburger = document.getElementById('hamburgerBtn');
    const navLinks = document.getElementById('navLinks');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('open');
        });
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navLinks.classList.remove('open');
            });
        });
    }

    // Mobile Map Toggle
    const mobileMapToggle = document.getElementById('mobileMapToggle');
    if (mobileMapToggle) {
        mobileMapToggle.addEventListener('click', () => {
            const isShowingMap = appContainer.classList.toggle('show-map-mobile');
            const mapIcon = mobileMapToggle.querySelector('.toggle-map-icon');
            const listIcon = mobileMapToggle.querySelector('.toggle-list-icon');
            const label = mobileMapToggle.querySelector('.toggle-label');

            if (isShowingMap) {
                if (mapIcon) mapIcon.style.display = 'none';
                if (listIcon) listIcon.style.display = 'block';
                if (label) label.textContent = 'List';
            } else {
                if (mapIcon) mapIcon.style.display = 'block';
                if (listIcon) listIcon.style.display = 'none';
                if (label) label.textContent = 'Map';
            }

            setTimeout(() => map && map.invalidateSize(), 100);
        });
    }
}

function initCustomDropdown(dropdownId, inputId) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;

    const btn = dropdown.querySelector('.custom-dropdown-btn');
    const label = dropdown.querySelector('span');
    const input = document.getElementById(inputId);
    const options = dropdown.querySelectorAll('.custom-option');

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.querySelectorAll('.custom-dropdown-container.open').forEach(d => {
            if (d !== dropdown) d.classList.remove('open');
        });
        dropdown.classList.toggle('open');
    });

    options.forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            options.forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');

            if (dropdownId === 'cityDropdown') {
                label.textContent = option.textContent;
                const coords = option.dataset.value.split(',');
                const lat = parseFloat(coords[0]);
                const lng = parseFloat(coords[1]);
                const cityName = option.dataset.name || option.textContent.replace(" Area", "");

                // Trigger complete city selection & load locations
                selectCity(cityName, lat, lng);
            } else {
                label.textContent = option.dataset.label;
            }

            if (input) {
                input.value = option.dataset.value;
            }

            dropdown.classList.remove('open');
        });
    });
}

/**
 * Handles selecting a city from either the menu dropdown or quick buttons
 * Updates coordinates, input text, dropdown labels, pans map, and immediately fetches locations!
 */
function selectCity(cityName, lat, lng) {
    userLat = lat;
    userLng = lng;
    currentCityName = cityName;

    // Update location input
    const locInput = document.getElementById('locationInput');
    if (locInput) {
        locInput.value = `${cityName}, Maharashtra`;
    }

    // Update Map view
    if (map) {
        map.setView([lat, lng], 13);
    }

    // Update quick city buttons active state
    document.querySelectorAll('.quick-city-btn').forEach(btn => {
        if (btn.dataset.name.toLowerCase() === cityName.toLowerCase()) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update city dropdown label and selected option
    const cityDropdown = document.getElementById('cityDropdown');
    if (cityDropdown) {
        const label = cityDropdown.querySelector('#cityDropdownLabel');
        if (label) label.textContent = `${cityName} Area`;

        cityDropdown.querySelectorAll('.custom-option').forEach(opt => {
            if ((opt.dataset.name || '').toLowerCase() === cityName.toLowerCase()) {
                opt.classList.add('selected');
            } else {
                opt.classList.remove('selected');
            }
        });
    }

    // Ensure categories are selected
    if (selectedCategories.size === 0) {
        document.querySelectorAll('.pill').forEach(c => {
            if (DEFAULT_SELECTED_CATS.includes(c.dataset.id)) {
                c.classList.add('selected');
                selectedCategories.add(c.dataset.id);
            }
        });
    }

    // Fetch and show the locations for this selected city!
    executeSearch(true);
}

function switchView(viewId) {
    document.querySelectorAll('.view-state').forEach(v => v.classList.remove('active'));
    const target = document.getElementById(viewId);
    if (target) target.classList.add('active');
    const overlay = document.getElementById('detailOverlay');
    if (overlay) overlay.classList.remove('active');
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

            // Pre-select default categories so user gets instant results
            if (DEFAULT_SELECTED_CATS.includes(cat.id)) {
                pill.classList.add('selected');
                selectedCategories.add(cat.id);
            }

            pill.addEventListener('click', () => {
                pill.classList.toggle('selected');
                if (selectedCategories.has(cat.id)) {
                    selectedCategories.delete(cat.id);
                } else {
                    selectedCategories.add(cat.id);
                }

                // If results view is active, update results live
                if (document.getElementById('resultsView').classList.contains('active')) {
                    executeSearch(false);
                }
            });
            grid.appendChild(pill);
        });

        // Automatically load initial locations for default city (Nashik)
        executeSearch(false);

    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

// ── Location ──
function detectLocation() {
    const btn = document.getElementById('detectLocationBtn');
    btn.innerHTML = `<svg width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg> Locating...`;

    if (!navigator.geolocation) {
        showError('Geolocation not supported by your browser.');
        btn.innerHTML = `Detect`;
        return;
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
            if (map) map.setView([userLat, userLng], 14);

            // Immediately show locations for detected location
            executeSearch(true);
        },
        () => {
            showError('Could not detect location. Please type your city.');
            btn.innerHTML = `Detect`;
        },
        { enableHighAccuracy: true, timeout: 5000 }
    );
}

// ── Search & Location Display ──
function showError(msg) {
    const err = document.getElementById('formError');
    if (!err) return;
    err.textContent = msg;
    err.style.display = 'block';
    setTimeout(() => { err.style.display = 'none'; }, 4000);
}

function handleSearch(e) {
    if (e) e.preventDefault();
    executeSearch(true);
}

async function executeSearch(autoSwitchView = true) {
    // If no category is selected, select all categories by default
    if (selectedCategories.size === 0) {
        document.querySelectorAll('.pill').forEach(c => {
            c.classList.add('selected');
            selectedCategories.add(c.dataset.id);
        });
    }

    const locInput = document.getElementById('locationInput');
    const locationText = locInput ? locInput.value.trim() : '';

    if (!locationText && (!userLat || !userLng)) {
        showError('Please select a city or enter an address.');
        return;
    }

    const btn = document.getElementById('submitBtn');
    const ogText = btn ? btn.textContent : 'Search Nearby';
    if (btn) {
        btn.textContent = 'Finding locations...';
        btn.disabled = true;
    }

    try {
        // Geocode if coordinates are missing
        if (!userLat || !userLng) {
            const geoResp = await fetch(`/api/geocode?q=${encodeURIComponent(locationText)}`);
            if (!geoResp.ok) throw new Error('Location not found. Try selecting a city from the buttons.');
            const geoData = await geoResp.json();
            if (geoData.error || !geoData.lat || !geoData.lng) {
                throw new Error('Location not found. Try selecting a city from the buttons.');
            }
            userLat = geoData.lat;
            userLng = geoData.lng;
        }

        const budgetEl = document.getElementById('budgetSelect');
        const radiusEl = document.getElementById('radiusSelect');
        const budget = budgetEl ? budgetEl.value : '';
        const radius = radiusEl ? radiusEl.value : '2000';

        const resp = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userLat,
                lng: userLng,
                categories: Array.from(selectedCategories),
                budget: budget ? parseInt(budget) : null,
                radius: parseInt(radius || 2000),
            }),
        });

        if (!resp.ok) {
            throw new Error(`Server returned error (${resp.status})`);
        }

        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        currentResults = data.results || {};
        updateMap(userLat, userLng, currentResults);
        renderResults(currentResults, data.summary);

        if (autoSwitchView) {
            switchView('resultsView');
        }

    } catch (err) {
        console.error('Search failed:', err);
        showError(err.message || 'Search failed. Please try another city.');
    } finally {
        if (btn) {
            btn.textContent = ogText;
            btn.disabled = false;
        }
    }
}

// ── Map ──
function initMap(lat, lng) {
    map = L.map('map', { zoomControl: false }).setView([lat, lng], 13);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
}

function updateMap(lat, lng, results) {
    if (!map || !markersLayer) return;
    markersLayer.clearLayers();

    // User Location Pin
    const userIcon = L.divIcon({
        className: 'user-marker',
        html: `<div style="width:24px;height:24px;background:var(--grad-primary, #6366f1);border:4px solid white;border-radius:50%;box-shadow:0 10px 15px -3px rgba(139,92,246,0.5)"></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    const locName = document.getElementById('locationInput')?.value || "Selected Location";
    L.marker([lat, lng], { icon: userIcon, zIndexOffset: 1000 })
        .bindPopup(`<b>${locName}</b><br>Search Center`)
        .addTo(markersLayer);

    const bounds = L.latLngBounds([[lat, lng]]);
    let markerCount = 0;

    // Results Pins
    for (const [catKey, places] of Object.entries(results)) {
        if (!Array.isArray(places)) continue;
        const color = MARKER_COLORS[catKey] || '#6366f1';
        const iconSymbol = categoriesData[catKey]?.icon || '📍';

        places.forEach(place => {
            if (!place.lat || !place.lng) return;
            markerCount++;

            const icon = L.divIcon({
                className: 'place-marker',
                html: `
                <div style="background:${color}; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-size:14px; border:3px solid white; box-shadow:0 8px 15px -3px rgba(0,0,0,0.2); cursor:pointer;">
                    ${iconSymbol}
                </div>`,
                iconSize: [32, 32],
                iconAnchor: [16, 16]
            });

            L.marker([place.lat, place.lng], { icon })
                .bindPopup(`<b>${place.name}</b><br>${place.distance_m}m away<br><small style="color:#6b7280">${place.address || ''}</small>`)
                .addTo(markersLayer)
                .on('click', () => openDetail(place.osm_type, place.place_id));

            bounds.extend([place.lat, place.lng]);
        });
    }

    if (markerCount > 0) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    } else {
        map.setView([lat, lng], 13);
    }
}

// ── Results Render ──
function renderResults(results, summary) {
    const totalFound = summary && summary.total_places_found !== undefined
        ? summary.total_places_found
        : Object.values(results).reduce((acc, list) => acc + (Array.isArray(list) ? list.length : 0), 0);

    const container = document.getElementById('resultsContainer');
    if (!container) return;
    container.innerHTML = '';

    const summaryText = document.getElementById('resultsSummaryText');
    if (summaryText) {
        summaryText.textContent = `Found ${totalFound} places in ${currentCityName}`;
    }

    for (const [catKey, places] of Object.entries(results)) {
        if (!Array.isArray(places) || places.length === 0) continue;
        const cat = categoriesData[catKey] || { icon: '📍', label: catKey };

        const catTitle = document.createElement('h3');
        catTitle.style.cssText = 'font-size:1.3rem; font-weight:700; margin: 28px 0 14px; display:flex; gap:10px; align-items:center;';
        catTitle.innerHTML = `<span>${cat.icon}</span> ${cat.label} <span style="background:#f3f4f6;color:#6b7280;padding:2px 10px;border-radius:20px;font-size:0.85rem">${places.length}</span>`;
        container.appendChild(catTitle);

        places.forEach(place => {
            const card = document.createElement('div');
            card.className = 'place-card';
            card.onclick = () => openDetail(place.osm_type, place.place_id);

            const dist = place.distance_m < 1000 ? `${place.distance_m}m` : `${(place.distance_m / 1000).toFixed(1)}km`;
            const score = place.scores ? Math.round(place.scores.composite * 100) : 75;

            card.innerHTML = `
                <div class="card-top">
                    <div>
                        <div class="card-title">${place.name}</div>
                        <div class="card-address">${place.address || 'Local Area'}</div>
                    </div>
                    <div class="card-dist">${dist}</div>
                </div>
                <div class="match-bar-container">
                    <div class="match-label"><span>Match Score</span> <span style="color:#8b5cf6; font-weight:600">${score}%</span></div>
                    <div class="m-track"><div class="m-fill" style="width:${score}%"></div></div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    if (container.children.length === 0) {
        container.innerHTML = `
            <div style="padding:40px;text-align:center;color:#6b7280;background:#f9fafb;border-radius:16px;margin-top:20px;">
                <p style="font-size:1.1rem;font-weight:600;margin-bottom:8px;">No places found</p>
                <p style="font-size:0.9rem;">Try selecting a different city from the menu or selecting more categories.</p>
            </div>`;
    }
}

// ── Item Detail ──
async function openDetail(osmType, placeId) {
    const overlay = document.getElementById('detailOverlay');
    const body = document.getElementById('detailBody');
    if (!overlay || !body) return;

    overlay.classList.add('active');
    body.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af">Loading details...</div>`;

    try {
        const resp = await fetch(`/api/place-details/${osmType || 'node'}/${placeId}`);
        const data = await resp.json();

        body.innerHTML = `
            <h2 class="detail-title">${data.name || 'Place Details'}</h2>
            <p class="detail-address">📍 ${data.address || 'Address unavailable'}</p>
            
            <div class="detail-info">
                ${data.cuisine ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>Cuisine</b><br/>${data.cuisine}</div>` : ''}
                ${data.phone ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>📱 Contact</b><br/>${data.phone}</div>` : ''}
                ${data.hours && data.hours.length ? `<div style="background:#f3f4f6;padding:12px 20px;border-radius:12px"><b>🕐 Hours</b><br/>${data.hours.join('<br>')}</div>` : ''}
            </div>

            <div style="margin-top:40px;display:flex;gap:16px;">
                <a href="${data.maps_url || '#'}" target="_blank" class="btn-action" style="flex:1;">🗺️ Open in OpenStreetMap</a>
                ${data.phone ? `<a href="tel:${data.phone}" class="btn-action" style="flex:1;background:var(--grad-primary);color:white">📞 Call</a>` : ''}
            </div>
        `;
    } catch {
        body.innerHTML = `<div class="error-msg">Failed to load details.</div>`;
    }
}
