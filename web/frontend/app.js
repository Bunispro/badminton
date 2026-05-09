let currentEvent = 'MS';
let currentModel = 'whr';
let currentMode = 'current';
let currentChart = null;
let currentLeaderboardData = [];

const modelNames = {
    'elo': 'Elo',
    'whr': 'WHR'
};

// DOM Elements
const leaderboardTable = document.querySelector('#leaderboard-table tbody');
const eventButtons = document.querySelectorAll('#event-buttons .btn');
const modelButtons = document.querySelectorAll('#model-buttons .btn');
const modeButtons = document.querySelectorAll('#mode-buttons .btn');
const currentTitle = document.querySelector('#current-title');
const predictBtn = document.querySelector('#predict-btn');
const p1Input = document.querySelector('#p1-input');
const p2Input = document.querySelector('#p2-input');
const predictResult = document.querySelector('#predict-result');
const toggleUncertainty = document.querySelector('#toggle-uncertainty');
const toggleGraphUncertainty = document.querySelector('#toggle-graph-uncertainty');
const settingsBtn = document.querySelector('#settings-btn');
const settingsDropdown = document.querySelector('#settings-dropdown');
const themeSelect = document.querySelector('#theme-select');
const accentSelect = document.querySelector('#accent-select');

// Detailed View Elements
const leaderboardView = document.querySelector('#leaderboard-view');
const detailedView = document.querySelector('#detailed-view');
const backBtn = document.querySelector('#back-btn');
const matchHistoryBody = document.querySelector('#match-history-body');
const startDateInput = document.querySelector('#start-date');
const endDateInput = document.querySelector('#end-date');
const tournamentSelect = document.querySelector('#tournament-select');
const tournamentList = document.querySelector('#tournament-list');

// Initialize
function init() {
    setupEventListeners();
    loadLeaderboard();
}

function setupEventListeners() {
    // Event buttons
    eventButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            eventButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentEvent = btn.dataset.event;
            updateTitle();
            
            // Close detailed view if open
            if (detailedView) detailedView.style.display = 'none';
            if (leaderboardView) leaderboardView.style.display = 'block';
            
            loadLeaderboard();
        });
    });

    // Model buttons
    modelButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modelButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentModel = btn.dataset.model;
            updateTitle();
            
            // Update detailed view if open
            if (detailedView && detailedView.style.display === 'block') {
                const playerName = document.querySelector('#detailed-player-name').textContent;
                const playerId = detailedView.dataset.playerId;
                showDetailedView(playerId, playerName);
            } else {
                loadLeaderboard();
            }
        });
    });

    // Mode buttons
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Do nothing if in detailed view
            if (detailedView && detailedView.style.display === 'block') {
                return;
            }
            
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            updateTitle();
            loadLeaderboard();
        });
    });

    // Predict
    predictBtn.addEventListener('click', handlePredict);

    // Toggle Uncertainty
    if (toggleUncertainty) {
        toggleUncertainty.addEventListener('change', () => {
            renderLeaderboard(currentLeaderboardData);
        });
    }

    // Toggle Graph Uncertainty
    if (toggleGraphUncertainty) {
        toggleGraphUncertainty.addEventListener('change', () => {
            const activeRow = leaderboardTable.querySelector('tr.active');
            if (activeRow) {
                const playerId = activeRow.dataset.id;
                const playerName = activeRow.cells[1].textContent;
                loadPlayerHistoryInline(playerId, playerName, 'inline-chart');
            }
        });
    }

    // Back Button in Detailed View
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            detailedView.style.display = 'none';
            leaderboardView.style.display = 'block';
        });
    }

    // Toggle Settings Dropdown
    if (settingsBtn) {
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = settingsDropdown.style.display === 'block';
            settingsDropdown.style.display = isVisible ? 'none' : 'block';
        });
        
        document.addEventListener('click', (e) => {
            if (settingsDropdown && !settingsDropdown.contains(e.target) && e.target !== settingsBtn) {
                settingsDropdown.style.display = 'none';
            }
        });
    }

    // Theme Select
    if (themeSelect) {
        themeSelect.addEventListener('change', (e) => {
            applyTheme(e.target.value);
        });
    }

    // Accent Select
    if (accentSelect) {
        accentSelect.addEventListener('change', (e) => {
            applyAccent(e.target.value);
        });
    }
}

function updateTitle() {
    const eventNames = {
        'MS': "Men's Singles",
        'WS': "Women's Singles",
        'MD': "Men's Doubles",
        'WD': "Women's Doubles",
        'XD': "Mixed Doubles"
    };
    const modelNames = {
        'whr': 'WHR',
        'elo': 'Elo'
    };
    const modeNames = {
        'current': 'Current',
        'peak': 'Peak of All Time'
    };
    currentTitle.textContent = `${eventNames[currentEvent]} - ${modelNames[currentModel]} (${modeNames[currentMode]})`;
}

async function loadLeaderboard() {
    leaderboardTable.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading...</td></tr>';
    
    try {
        const response = await fetch(`/api/leaderboard?event=${currentEvent}&model=${currentModel}&mode=${currentMode}`);
        if (!response.ok) throw new Error('Failed to fetch leaderboard');
        const data = await response.json();
        
        currentLeaderboardData = data;
        renderLeaderboard(data);
    } catch (error) {
        console.error(error);
        leaderboardTable.innerHTML = '<tr><td colspan="4" style="text-align:center;color:red;">Error loading data</td></tr>';
    }
}

function renderLeaderboard(data) {
    leaderboardTable.innerHTML = '';
    
    if (data.length === 0) {
        leaderboardTable.innerHTML = '<tr><td colspan="4" style="text-align:center;">No data available</td></tr>';
        return;
    }
    
    // Update header text based on mode
    const headerRow = leaderboardTable.parentElement.querySelector('thead tr');
    if (headerRow) {
        headerRow.cells[3].textContent = currentMode === 'peak' ? 'Peak Date' : 'Last Updated';
    }
    
    data.forEach((player, index) => {
        const row = document.createElement('tr');
        row.dataset.id = player.player_id;
        
        const showUncertainty = toggleUncertainty && toggleUncertainty.checked;
        const ratingDisplay = showUncertainty ? `${player.rating} ± ${(player.uncertainty || 0)}` : player.rating;
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${player.name}</td>
            <td style="font-weight:600;color:var(--accent-color);">${ratingDisplay}</td>
            <td style="color:var(--text-dim);">${player.date}</td>
        `;
        
        row.addEventListener('click', () => {
            const isExpanding = !row.classList.contains('active');
            
            if (isExpanding) {
                row.classList.add('active');
                
                // Create a new row for the chart
                const chartRow = document.createElement('tr');
                chartRow.classList.add('chart-row');
                
                const canvasId = `chart-${player.player_id}`;
                chartRow.innerHTML = `
                    <td colspan="4">
                        <div style="height: 250px; width: 100%; position: relative;">
                            <canvas id="${canvasId}"></canvas>
                            <button class="detailed-history-btn" style="position: absolute; top: 10px; right: 10px; background: var(--accent-color); color: white; border: none; padding: 0.25rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.75rem;">Detailed History</button>
                        </div>
                    </td>
                `;
                
                row.insertAdjacentElement('afterend', chartRow);
                loadPlayerHistoryInline(player.player_id, player.name, canvasId);
                
                // Auto-focus
                chartRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Add listener for detailed history button
                chartRow.querySelector('.detailed-history-btn').addEventListener('click', (e) => {
                    e.stopPropagation(); // Don't collapse the row
                    showDetailedView(player.player_id, player.name);
                });
            } else {
                row.classList.remove('active');
                // Find and remove the chart row
                const nextRow = row.nextElementSibling;
                if (nextRow && nextRow.classList.contains('chart-row')) {
                    nextRow.remove();
                }
            }
        });
        
        leaderboardTable.appendChild(row);
    });
}

async function loadPlayerHistory(playerId, playerName) {
    chartContainer.style.display = 'none';
    noChartMsg.style.display = 'flex';
    noChartMsg.textContent = 'Loading chart...';
    
    try {
        const response = await fetch(`/api/player/${playerId}/history?event=${currentEvent}&model=${currentModel}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();
        
        if (data.length === 0) {
            noChartMsg.textContent = 'No history data for this player';
            return;
        }
        
        noChartMsg.style.display = 'none';
        chartContainer.style.display = 'block';
        
        renderChart(data, playerName);
    } catch (error) {
        console.error(error);
        noChartMsg.textContent = 'Error loading chart';
    }
}

function renderChart(data, playerName) {
    const ctx = document.getElementById('history-chart').getContext('2d');
    
    const labels = data.map(d => d.date);
    const ratings = data.map(d => d.rating);
    const upperBounds = data.map(d => d.rating + d.uncertainty);
    const lowerBounds = data.map(d => d.rating - d.uncertainty);
    
    if (currentChart) {
        currentChart.destroy();
    }
    
    currentChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Upper Bound',
                    data: upperBounds,
                    borderColor: 'transparent',
                    backgroundColor: 'transparent',
                    pointRadius: 0,
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Lower Bound',
                    data: lowerBounds,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    pointRadius: 0,
                    fill: '-1', // Fill to previous dataset
                    tension: 0.1
                },
                {
                    label: `${playerName} Rating`,
                    data: ratings,
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 1,
                    pointHoverRadius: 5,
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f8fafc',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            }
        }
    });
}

async function handlePredict() {
    const p1 = p1Input.value.trim();
    const p2 = p2Input.value.trim();
    
    if (!p1 || !p2) {
        predictResult.innerHTML = '<span style="color:red;">Enter both IDs</span>';
        return;
    }
    
    predictResult.innerHTML = 'Calculating...';
    
    try {
        const response = await fetch(`/api/predict?p1=${p1}&p2=${p2}&event=${currentEvent}&model=${currentModel}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Prediction failed');
        }
        const data = await response.json();
        
        predictResult.innerHTML = `
            <div><strong>Probabilities:</strong></div>
            <div style="display:flex; justify-content:space-between; margin-top:0.5rem;">
                <span>Player 1: ${(data.prob_p1 * 100).toFixed(1)}%</span>
                <span>Player 2: ${(data.prob_p2 * 100).toFixed(1)}%</span>
            </div>
            <div style="font-size:0.75rem; margin-top:0.5rem; color:var(--text-dim);">
                Ratings: ${data.r1} vs ${data.r2}
            </div>
        `;
    } catch (error) {
        console.error(error);
        predictResult.innerHTML = `<span style="color:red;">${error.message}</span>`;
    }
}

async function loadPlayerHistoryInline(playerId, playerName, canvasId) {
    try {
        const response = await fetch(`/api/player/${playerId}/history?event=${currentEvent}&model=${currentModel}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();
        
        if (data.length === 0) {
            document.getElementById(canvasId).parentElement.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-dim);">No history data for this player</div>';
            return;
        }
        
        renderChartInline(data, playerName, canvasId);
    } catch (error) {
        console.error(error);
        document.getElementById(canvasId).parentElement.innerHTML = '<div style="text-align:center;padding:2rem;color:red;">Error loading chart</div>';
    }
}

function renderChartInline(data, playerName, canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const labels = data.map(d => d.date.substring(0, 4));
    const ratings = data.map(d => d.rating);
    const upperBounds = data.map(d => d.rating + (d.uncertainty || 0));
    const lowerBounds = data.map(d => d.rating - (d.uncertainty || 0));
    
    const showShadedArea = toggleGraphUncertainty && toggleGraphUncertainty.checked;
    
    // Find peak point
    const maxRating = Math.max(...ratings);
    const peakIndex = ratings.indexOf(maxRating);
    
    const pointBackgroundColors = ratings.map((r, i) => i === peakIndex && currentMode === 'peak' ? '#ef4444' : '#10b981');
    const pointRadii = ratings.map((r, i) => i === peakIndex && currentMode === 'peak' ? 6 : 0);
    
    const datasets = [];
    
    if (showShadedArea) {
        datasets.push({
            label: 'Upper Bound',
            data: upperBounds,
            borderColor: 'transparent',
            backgroundColor: 'transparent',
            pointRadius: 0,
            fill: false,
            tension: 0.4
        });
        datasets.push({
            label: 'Lower Bound',
            data: lowerBounds,
            borderColor: 'transparent',
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            pointRadius: 0,
            fill: '-1',
            tension: 0.4
        });
    }
    
    datasets.push({
        label: `${playerName} Rating`,
        data: ratings,
        borderColor: '#10b981',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: pointRadii,
        pointBackgroundColor: pointBackgroundColors,
        pointHoverRadius: 5,
        fill: false,
        tension: 0.4
    });
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', maxRotation: 0, minRotation: 0 }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f8fafc',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        title: function(context) {
                            return data[context[0].dataIndex].date; // Show full date in tooltip
                        }
                    }
                }
            }
        }
    });
}

let detailedChart = null;

async function showDetailedView(playerId, playerName) {
    if (!leaderboardView || !detailedView) return;
    
    leaderboardView.style.display = 'none';
    detailedView.style.display = 'block';
    
    // Set player ID on dataset for sidebar interaction
    detailedView.dataset.playerId = playerId;
    
    // Update header
    document.querySelector('#detailed-player-name').textContent = playerName;
    document.querySelector('#detailed-model-info').textContent = `Model: ${modelNames[currentModel]} (${currentMode === 'peak' ? 'Peak' : 'Current'}) | ID: ${playerId}`;
    
    // Reset filters
    if (startDateInput) startDateInput.value = '';
    if (endDateInput) endDateInput.value = '';
    if (tournamentSelect) tournamentSelect.value = '';
    if (tournamentList) tournamentList.innerHTML = '';
    
    // Load history for graph
    try {
        const response = await fetch(`/api/player/${playerId}/history?event=${currentEvent}&model=${currentModel}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();
        
        console.log(`Fetched ${data.length} history points`);
        renderDetailedChart(data, playerName);
    } catch (error) {
        console.error(error);
        document.querySelector('#detailed-model-info').textContent += ` | Err: ${error.message}`;
    }
    
    // Load matches
    try {
        if (matchHistoryBody) matchHistoryBody.innerHTML = '<tr><td colspan="7" style="text-align:center; background: yellow; color: black;">DEBUG: Loading matches...</td></tr>';
        
        const response = await fetch(`/api/player/${playerId}/matches`);
        if (!response.ok) throw new Error('Failed to fetch matches');
        const matches = await response.json();
        
        console.log(`Fetched ${matches.length} matches`);
        if (matchHistoryBody) matchHistoryBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">Fetched ${matches.length} matches. Rendering...</td></tr>`;
        
        // Populate tournament filter
        const tournaments = [...new Set(matches.map(m => m.tournament))].filter(Boolean);
        if (tournamentList) {
            tournaments.forEach(t => {
                const option = document.createElement('option');
                option.value = t;
                tournamentList.appendChild(option);
            });
        }
        
        // Render matches
        renderMatches(matches);
        
        // Add filter listeners
        const applyFilters = () => {
            const start = startDateInput ? startDateInput.value : '';
            const end = endDateInput ? endDateInput.value : '';
            const selectedTournament = tournamentSelect ? tournamentSelect.value : '';
            
            const filtered = matches.filter(m => {
                const matchDate = m.date;
                const matchesDateRange = (!start || matchDate >= start) && (!end || matchDate <= end);
                const matchesTournament = !selectedTournament || m.tournament === selectedTournament;
                return matchesDateRange && matchesTournament;
            });
            
            renderMatches(filtered);
        };
        
        if (startDateInput) startDateInput.onchange = applyFilters;
        if (endDateInput) endDateInput.onchange = applyFilters;
        if (tournamentSelect) tournamentSelect.oninput = applyFilters;
        
        // Store matches globally for click handler
        window.currentMatches = matches;
        
    } catch (error) {
        console.error(error);
        if (matchHistoryBody) matchHistoryBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:red;">Error loading matches</td></tr>';
    }
}

function renderDetailedChart(data, playerName) {
    const canvas = document.getElementById('detailed-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (detailedChart) {
        detailedChart.destroy();
    }
    
    const labels = data.map(d => d.date.substring(0, 4));
    const ratings = data.map(d => d.rating);
    
    detailedChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${playerName} Rating`,
                data: ratings,
                borderColor: '#10b981',
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 5,
                fill: false,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return data[context[0].dataIndex].date;
                        }
                    }
                }
            },
            onClick: (e) => {
                const points = detailedChart.getElementsAtEventForMode(e, 'nearest', { intersect: false }, false);
                if (points.length > 0) {
                    const index = points[0].index;
                    const clickedDate = data[index].date;
                    
                    const matches = window.currentMatches;
                    if (matches) {
                        const rows = matchHistoryBody.querySelectorAll('tr');
                        rows.forEach(r => r.classList.remove('active'));
                        
                        // Find the row with the exact date or the closest one!
                        // For simplicity, let's find the first row that matches the year and month if exact date not found!
                        let targetRow = Array.from(rows).find(r => r.cells[0].textContent === clickedDate);
                        
                        if (!targetRow) {
                            // Find closest date!
                            // Let's just find the first row that starts with the same year!
                            const year = clickedDate.substring(0, 4);
                            targetRow = Array.from(rows).find(r => r.cells[0].textContent.startsWith(year));
                        }
                        
                        if (targetRow) {
                            targetRow.classList.add('active');
                            targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                }
            }
        }
    });
}

function renderMatches(matches) {
    if (!matchHistoryBody) return;
    matchHistoryBody.innerHTML = '';
    
    if (matches.length === 0) {
        matchHistoryBody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No matches found</td></tr>';
        return;
    }
    
    matches.forEach(m => {
        const row = document.createElement('tr');
        
        const opponents = m.opponents.map(o => o.name).join(', ');
        const isWinner = m.winner_side === m.player_side;
        const resultDisplay = isWinner ? '<span style="color:#10b981;font-weight:600;">W</span>' : '<span style="color:#ef4444;font-weight:600;">L</span>';
        
        row.innerHTML = `
            <td>${m.date}</td>
            <td>${m.tournament || '-'}</td>
            <td>${m.event || '-'}</td>
            <td>${m.round || '-'}</td>
            <td>${opponents || '-'}</td>
            <td>${m.score || '-'}</td>
            <td>${resultDisplay}</td>
        `;
        
        matchHistoryBody.appendChild(row);
    });
}

function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'light') {
        root.style.setProperty('--bg-color', '#f8fafc');
        root.style.setProperty('--card-bg', 'rgba(255, 255, 255, 0.7)');
        root.style.setProperty('--sidebar-bg', 'rgba(241, 245, 249, 0.8)');
        root.style.setProperty('--text-color', '#0f172a');
        root.style.setProperty('--text-dim', '#475569');
        root.style.setProperty('--border-color', 'rgba(0, 0, 0, 0.1)');
    } else if (theme === 'dim') {
        root.style.setProperty('--bg-color', '#1e293b');
        root.style.setProperty('--card-bg', 'rgba(15, 23, 42, 0.7)');
        root.style.setProperty('--sidebar-bg', 'rgba(15, 23, 42, 0.8)');
        root.style.setProperty('--text-color', '#f8fafc');
        root.style.setProperty('--text-dim', '#94a3b8');
        root.style.setProperty('--border-color', 'rgba(255, 255, 255, 0.1)');
    } else if (theme === 'lights-out') {
        root.style.setProperty('--bg-color', '#000000');
        root.style.setProperty('--card-bg', 'rgba(20, 20, 20, 0.7)');
        root.style.setProperty('--sidebar-bg', 'rgba(10, 10, 10, 0.8)');
        root.style.setProperty('--text-color', '#f8fafc');
        root.style.setProperty('--text-dim', '#64748b');
        root.style.setProperty('--border-color', 'rgba(255, 255, 255, 0.05)');
    } else { // Dark
        root.style.setProperty('--bg-color', '#0f172a');
        root.style.setProperty('--card-bg', 'rgba(30, 41, 59, 0.7)');
        root.style.setProperty('--sidebar-bg', 'rgba(15, 23, 42, 0.8)');
        root.style.setProperty('--text-color', '#f8fafc');
        root.style.setProperty('--text-dim', '#94a3b8');
        root.style.setProperty('--border-color', 'rgba(255, 255, 255, 0.1)');
    }
}

function applyAccent(accent) {
    const root = document.documentElement;
    const colors = {
        emerald: { color: '#10b981', glow: 'rgba(16, 185, 129, 0.3)' },
        blue: { color: '#3b82f6', glow: 'rgba(59, 130, 246, 0.3)' },
        purple: { color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.3)' },
        gold: { color: '#eab308', glow: 'rgba(234, 179, 8, 0.3)' }
    };
    
    const selected = colors[accent] || colors.emerald;
    root.style.setProperty('--accent-color', selected.color);
    root.style.setProperty('--accent-glow', selected.glow);
    
    // Update chart if it exists
    const inlineChart = document.getElementById('inline-chart');
    if (inlineChart) {
        // We would need to re-render or update the chart color here if we want it to be dynamic!
        // For now, it will apply to new charts!
    }
}

// Run
init();
