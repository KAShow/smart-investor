/**
 * Bahrain Interactive Map - Smart Investor
 * 4 Layers: Competitors, Demand Heatmap, Industrial/Commercial Zones, Governorates
 */

// HTML escape to prevent XSS
function _escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Industrial & Commercial Zones
const ZONES = {
    industrial: [
        { name: "BIIP", name_ar: "المنطقة الصناعية الاستثمارية", lat: 26.0833, lng: 50.5167, type: "صناعية" },
        { name: "Hidd Industrial", name_ar: "منطقة الحد الصناعية", lat: 26.2333, lng: 50.6500, type: "صناعية" },
        { name: "Sitra Industrial", name_ar: "منطقة سترة الصناعية", lat: 26.1500, lng: 50.6167, type: "صناعية" },
        { name: "Ma'ameer Industrial", name_ar: "منطقة المعامير الصناعية", lat: 26.1000, lng: 50.5500, type: "صناعية" },
        { name: "Salman Industrial City", name_ar: "مدينة سلمان الصناعية", lat: 26.1167, lng: 50.5333, type: "صناعية" }
    ],
    commercial: [
        { name: "Seef District", name_ar: "منطقة السيف", lat: 26.2400, lng: 50.5300, type: "تجارية" },
        { name: "Bahrain Financial Harbour", name_ar: "مرفأ البحرين المالي", lat: 26.2350, lng: 50.5750, type: "مالية" },
        { name: "Bahrain Bay", name_ar: "خليج البحرين", lat: 26.2450, lng: 50.5650, type: "تجارية" },
        { name: "Diplomatic Area", name_ar: "المنطقة الدبلوماسية", lat: 26.2300, lng: 50.5800, type: "مالية/تجارية" },
        { name: "Manama Souq", name_ar: "سوق المنامة", lat: 26.2250, lng: 50.5850, type: "تجارية تقليدية" }
    ]
};

// Governorates with population data
const GOVERNORATES = {
    capital: {
        name_ar: "محافظة العاصمة",
        name_en: "Capital",
        population: 520000,
        purchasing_power: "عالية",
        purchasing_power_en: "High",
        color: "#1565C0",
        center: [26.235, 50.585],
        bounds: [[26.20, 50.55], [26.27, 50.62]]
    },
    muharraq: {
        name_ar: "محافظة المحرق",
        name_en: "Muharraq",
        population: 290000,
        purchasing_power: "متوسطة-عالية",
        purchasing_power_en: "Medium-High",
        color: "#2E7D32",
        center: [26.265, 50.625],
        bounds: [[26.23, 50.59], [26.30, 50.66]]
    },
    northern: {
        name_ar: "المحافظة الشمالية",
        name_en: "Northern",
        population: 360000,
        purchasing_power: "متوسطة",
        purchasing_power_en: "Medium",
        color: "#F57F17",
        center: [26.215, 50.500],
        bounds: [[26.15, 50.44], [26.28, 50.56]]
    },
    southern: {
        name_ar: "المحافظة الجنوبية",
        name_en: "Southern",
        population: 370000,
        purchasing_power: "متوسطة-منخفضة",
        purchasing_power_en: "Medium-Low",
        color: "#C62828",
        center: [26.045, 50.535],
        bounds: [[25.93, 50.45], [26.16, 50.62]]
    }
};

// Sector → Recommended locations mapping
const SECTOR_LOCATIONS = {
    food_hospitality: ["Seef District", "Diplomatic Area", "Manama Souq"],
    real_estate: ["Bahrain Financial Harbour", "Bahrain Bay", "Seef District"],
    technology: ["Bahrain Bay", "Seef District", "Bahrain Financial Harbour"],
    finance: ["Bahrain Financial Harbour", "Diplomatic Area", "Bahrain Bay"],
    manufacturing: ["BIIP", "Salman Industrial City", "Sitra Industrial"],
    health: ["Seef District", "Diplomatic Area"],
    education: ["Seef District", "Manama Souq"],
    transport: ["Hidd Industrial", "Sitra Industrial", "BIIP"],
    retail: ["Seef District", "Manama Souq", "Bahrain Bay"],
    ai_applications: ["Bahrain Bay", "Seef District", "Bahrain Financial Harbour"]
};

// Governorate-based demand heatmap data (lat, lng, intensity)
const DEMAND_HEATMAP = [
    // Capital - high density
    [26.235, 50.585, 1.0], [26.230, 50.580, 0.9], [26.240, 50.575, 0.85],
    [26.225, 50.590, 0.8], [26.238, 50.570, 0.75], [26.232, 50.595, 0.7],
    // Seef/Juffair area
    [26.240, 50.530, 0.95], [26.245, 50.535, 0.9], [26.235, 50.525, 0.85],
    // Muharraq
    [26.260, 50.620, 0.6], [26.265, 50.630, 0.55], [26.270, 50.625, 0.5],
    // Northern
    [26.220, 50.500, 0.5], [26.210, 50.490, 0.45], [26.200, 50.480, 0.4],
    // Southern - Riffa
    [26.130, 50.555, 0.45], [26.120, 50.560, 0.4], [26.100, 50.550, 0.35],
    // Southern - Isa Town
    [26.170, 50.540, 0.4], [26.165, 50.535, 0.35]
];


/**
 * Initialize the Bahrain map inside the given container element.
 * @param {string} containerId - HTML element ID for the map
 * @param {string} sector - Selected sector key
 * @param {Array} competitors - Array of competitor objects from Sijilat data
 * @param {string} lang - 'ar' or 'en'
 * @returns {object} map instance + layer control
 */
function initBahrainMap(containerId, sector, competitors, lang) {
    const isAr = lang === 'ar';
    const container = document.getElementById(containerId);
    if (!container) return null;

    // Initialize map centered on Bahrain
    const map = L.map(containerId, {
        center: [26.15, 50.55],
        zoom: 11,
        zoomControl: true,
        attributionControl: true
    });

    // Tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // ===== Layer 1: Competitors =====
    const competitorsLayer = L.layerGroup();
    if (competitors && competitors.length) {
        // Assign approximate coordinates based on governorate
        const govCoords = {
            'العاصمة': [26.235, 50.585], 'Capital': [26.235, 50.585],
            'المحرق': [26.265, 50.625], 'Muharraq': [26.265, 50.625],
            'الشمالية': [26.215, 50.500], 'Northern': [26.215, 50.500],
            'الجنوبية': [26.045, 50.535], 'Southern': [26.045, 50.535]
        };
        competitors.forEach((comp, i) => {
            const gov = comp.governorate || '';
            let coords = govCoords[gov] || [26.20 + (Math.random() * 0.08), 50.50 + (Math.random() * 0.1)];
            // Slight offset to avoid stacking
            coords = [coords[0] + (Math.random() - 0.5) * 0.015, coords[1] + (Math.random() - 0.5) * 0.015];

            const size = comp.size || '';
            const color = size === 'كبيرة' || size === 'large' ? '#ef4444' :
                          size === 'متوسطة' || size === 'medium' ? '#f59e0b' : '#3b82f6';
            const radius = size === 'كبيرة' || size === 'large' ? 10 :
                           size === 'متوسطة' || size === 'medium' ? 8 : 6;

            const name = comp.name_ar || comp.name_en || '';
            const marker = L.circleMarker(coords, {
                radius: radius,
                fillColor: color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });
            marker.bindPopup(`<b>${_escHtml(name)}</b><br>${_escHtml(comp.activity || '')}<br>${isAr ? 'تأسست' : 'Est.'}: ${_escHtml(comp.established || '?')}<br>${isAr ? 'الحجم' : 'Size'}: ${_escHtml(size)}`);
            competitorsLayer.addLayer(marker);
        });
    }

    // ===== Layer 2: Demand Heatmap =====
    let heatLayer = null;
    if (typeof L.heatLayer === 'function') {
        heatLayer = L.heatLayer(DEMAND_HEATMAP, {
            radius: 30,
            blur: 25,
            maxZoom: 14,
            gradient: { 0.2: '#2196F3', 0.4: '#4CAF50', 0.6: '#FFEB3B', 0.8: '#FF9800', 1.0: '#F44336' }
        });
    }

    // ===== Layer 3: Industrial & Commercial Zones =====
    const zonesLayer = L.layerGroup();
    ZONES.industrial.forEach(z => {
        const marker = L.marker([z.lat, z.lng], {
            icon: L.divIcon({
                className: 'zone-marker',
                html: `<div style="background:#FF6F00;color:#fff;padding:3px 6px;border-radius:4px;font-size:10px;font-weight:bold;white-space:nowrap;border:1px solid #E65100">${isAr ? z.name_ar : z.name}</div>`,
                iconSize: null,
                iconAnchor: [60, 12]
            })
        });
        marker.bindPopup(`<b>${isAr ? z.name_ar : z.name}</b><br>${isAr ? 'النوع' : 'Type'}: ${z.type}`);
        zonesLayer.addLayer(marker);
    });
    ZONES.commercial.forEach(z => {
        const marker = L.marker([z.lat, z.lng], {
            icon: L.divIcon({
                className: 'zone-marker',
                html: `<div style="background:#1565C0;color:#fff;padding:3px 6px;border-radius:4px;font-size:10px;font-weight:bold;white-space:nowrap;border:1px solid #0D47A1">${isAr ? z.name_ar : z.name}</div>`,
                iconSize: null,
                iconAnchor: [60, 12]
            })
        });
        marker.bindPopup(`<b>${isAr ? z.name_ar : z.name}</b><br>${isAr ? 'النوع' : 'Type'}: ${z.type}`);
        zonesLayer.addLayer(marker);
    });

    // ===== Layer 4: Governorates =====
    const govLayer = L.layerGroup();
    Object.values(GOVERNORATES).forEach(gov => {
        const rect = L.rectangle(gov.bounds, {
            color: gov.color,
            weight: 2,
            fillColor: gov.color,
            fillOpacity: 0.1,
            dashArray: '5,5'
        });
        const popStr = isAr
            ? `<b>${gov.name_ar}</b><br>السكان: ${gov.population.toLocaleString()}<br>القدرة الشرائية: ${gov.purchasing_power}`
            : `<b>${gov.name_en}</b><br>Population: ${gov.population.toLocaleString()}<br>Purchasing Power: ${gov.purchasing_power_en}`;
        rect.bindPopup(popStr);
        govLayer.addLayer(rect);

        // Population label
        const label = L.marker(gov.center, {
            icon: L.divIcon({
                className: 'gov-label',
                html: `<div style="text-align:center;font-size:11px;font-weight:700;color:${gov.color};text-shadow:0 0 3px #fff,0 0 3px #fff">${isAr ? gov.name_ar : gov.name_en}<br><span style="font-size:10px;font-weight:400">${gov.population.toLocaleString()}</span></div>`,
                iconSize: [120, 40],
                iconAnchor: [60, 20]
            })
        });
        govLayer.addLayer(label);
    });

    // ===== Recommended locations highlight =====
    const recLayer = L.layerGroup();
    const recNames = SECTOR_LOCATIONS[sector] || [];
    const allZones = [...ZONES.industrial, ...ZONES.commercial];
    recNames.forEach(name => {
        const zone = allZones.find(z => z.name === name);
        if (zone) {
            const pulse = L.circleMarker([zone.lat, zone.lng], {
                radius: 18,
                fillColor: '#4CAF50',
                color: '#4CAF50',
                weight: 3,
                opacity: 0.8,
                fillOpacity: 0.2
            });
            pulse.bindPopup(`<b style="color:#4CAF50">${isAr ? 'موقع موصى به' : 'Recommended Location'}</b><br>${isAr ? zone.name_ar : zone.name}`);
            recLayer.addLayer(pulse);
        }
    });

    // Add default layers
    competitorsLayer.addTo(map);
    zonesLayer.addTo(map);
    govLayer.addTo(map);
    recLayer.addTo(map);

    // Layer control
    const overlays = {};
    overlays[isAr ? 'المنافسون' : 'Competitors'] = competitorsLayer;
    if (heatLayer) {
        overlays[isAr ? 'كثافة الطلب' : 'Demand Heatmap'] = heatLayer;
    }
    overlays[isAr ? 'المناطق الصناعية والتجارية' : 'Industrial & Commercial Zones'] = zonesLayer;
    overlays[isAr ? 'المحافظات' : 'Governorates'] = govLayer;
    overlays[isAr ? 'المواقع الموصى بها' : 'Recommended Locations'] = recLayer;

    L.control.layers(null, overlays, { collapsed: false, position: 'topright' }).addTo(map);

    // Build recommendation text
    let recText = '';
    if (recNames.length) {
        const recAr = recNames.map(n => {
            const z = allZones.find(z => z.name === n);
            return z ? (isAr ? z.name_ar : z.name) : n;
        });
        recText = isAr
            ? `المواقع الموصى بها لقطاعك: ${recAr.join('، ')}`
            : `Recommended locations for your sector: ${recAr.join(', ')}`;
    }

    return { map, recText };
}
