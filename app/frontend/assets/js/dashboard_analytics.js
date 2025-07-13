/**
 * MARSLOG Dashboard Analytics JavaScript
 * Kibana-like interface with real-time data
 */

class MarslogDashboard {
    constructor() {
        this.autoRefresh = true;
        this.refreshInterval = 30000; // 30 seconds
        this.currentView = 'overview';
        this.timeRange = '6h';
        this.charts = {};
        this.websocket = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadDashboardData();
        this.startAutoRefresh();
        this.connectWebSocket();
    }

    setupEventListeners() {
        // Sidebar navigation
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });

        // Time range picker
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.timeRange = e.currentTarget.dataset.range;
                this.loadDashboardData();
            });
        });

        // Search functionality
        const searchInput = document.getElementById('log-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchLogs();
                }
            });
        }
    }

    switchView(viewName) {
        // Update sidebar
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

        // Hide all views
        document.querySelectorAll('.dashboard-view').forEach(view => {
            view.style.display = 'none';
        });

        // Show selected view
        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.style.display = 'block';
            this.currentView = viewName;
            
            // Load view-specific data
            this.loadViewData(viewName);
        }
    }

    async loadViewData(viewName) {
        switch (viewName) {
            case 'overview':
                await this.loadOverviewData();
                break;
            case 'logs':
                await this.loadLogStream();
                break;
            case 'search':
                await this.loadSearchResults();
                break;
            case 'patterns':
                await this.loadPatternAnalysis();
                break;
            case 'threats':
                await this.loadThreatData();
                break;
            case 'performance':
                await this.loadPerformanceData();
                break;
        }
    }

    initializeCharts() {
        // Events Timeline Chart
        const timelineCtx = document.getElementById('events-timeline-chart');
        if (timelineCtx) {
            this.charts.eventsTimeline = new Chart(timelineCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Events per minute',
                        data: [],
                        borderColor: '#1BA2E6',
                        backgroundColor: 'rgba(27, 162, 230, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#b3b3b3' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#666666' },
                            grid: { color: '#3a3a3a' }
                        },
                        y: {
                            ticks: { color: '#666666' },
                            grid: { color: '#3a3a3a' }
                        }
                    }
                }
            });
        }

        // Log Levels Chart
        const levelsCtx = document.getElementById('log-levels-chart');
        if (levelsCtx) {
            this.charts.logLevels = new Chart(levelsCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Info', 'Warning', 'Error', 'Debug'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#1BA2E6', '#FF9500', '#FF6B6B', '#666666'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#b3b3b3' }
                        }
                    }
                }
            });
        }

        // Pattern Analysis Chart
        const patternsCtx = document.getElementById('patterns-chart');
        if (patternsCtx) {
            this.charts.patterns = new Chart(patternsCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Frequency',
                        data: [],
                        backgroundColor: '#9C27B0'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {
                        legend: {
                            labels: { color: '#b3b3b3' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#666666' },
                            grid: { color: '#3a3a3a' }
                        },
                        y: {
                            ticks: { color: '#666666' },
                            grid: { color: '#3a3a3a' }
                        }
                    }
                }
            });
        }
    }

    async loadDashboardData() {
        try {
            const response = await fetch(`/api/dashboard/stats?range=${this.timeRange}`);
            const data = await response.json();
            
            this.updateStatistics(data.stats);
            this.updateCharts(data.charts);
            this.updateRecentEvents(data.recent_events);
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    async loadOverviewData() {
        try {
            // Load overview statistics
            const [statsResponse, timelineResponse] = await Promise.all([
                fetch(`/api/analytics/overview?range=${this.timeRange}`),
                fetch(`/api/analytics/timeline?range=${this.timeRange}`)
            ]);

            const stats = await statsResponse.json();
            const timeline = await timelineResponse.json();

            this.updateStatistics(stats);
            this.updateTimelineChart(timeline);

        } catch (error) {
            console.error('Error loading overview data:', error);
        }
    }

    async loadLogStream() {
        try {
            const response = await fetch(`/api/logs/stream?limit=100&range=${this.timeRange}`);
            const logs = await response.json();
            
            this.updateLogStream(logs);
            
        } catch (error) {
            console.error('Error loading log stream:', error);
        }
    }

    async loadPatternAnalysis() {
        try {
            const response = await fetch(`/api/ai-parser/patterns`);
            const patterns = await response.json();
            
            this.updatePatternsChart(patterns);
            
        } catch (error) {
            console.error('Error loading pattern analysis:', error);
        }
    }

    async loadPerformanceData() {
        try {
            const response = await fetch('/api/syslog/status');
            const performance = await response.json();
            
            this.updatePerformanceStats(performance);
            
        } catch (error) {
            console.error('Error loading performance data:', error);
        }
    }

    updateStatistics(stats) {
        const elements = {
            'total-events': stats.total_events || 0,
            'error-rate': `${(stats.error_rate || 0).toFixed(1)}%`,
            'active-sources': stats.active_sources || 0,
            'events-per-second': stats.current_eps || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                this.animateValue(element, value);
            }
        });
    }

    updateTimelineChart(timelineData) {
        if (this.charts.eventsTimeline && timelineData) {
            this.charts.eventsTimeline.data.labels = timelineData.labels || [];
            this.charts.eventsTimeline.data.datasets[0].data = timelineData.data || [];
            this.charts.eventsTimeline.update('none');
        }
    }

    updateLogStream(logs) {
        const logContainer = document.getElementById('log-stream');
        if (!logContainer || !logs) return;

        logContainer.innerHTML = '';

        logs.forEach(log => {
            const logEntry = this.createLogEntry(log);
            logContainer.appendChild(logEntry);
        });

        // Auto-scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    createLogEntry(log) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const timestamp = new Date(log.timestamp || log.received_at).toLocaleTimeString();
        const level = (log.severity_name || log.level || 'info').toLowerCase();
        const source = log.hostname || log.source_ip || 'unknown';
        const message = log.message || log.raw_message || '';

        entry.innerHTML = `
            <div class="log-timestamp">${timestamp}</div>
            <div class="log-level ${level}">${level}</div>
            <div class="log-source">${source}</div>
            <div class="log-message">${this.escapeHtml(message)}</div>
        `;

        return entry;
    }

    updateRecentEvents(events) {
        const tableContainer = document.getElementById('recent-events-table');
        if (!tableContainer || !events) return;

        tableContainer.innerHTML = '';

        events.forEach(event => {
            const row = document.createElement('div');
            row.className = 'table-row';
            
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            const level = event.severity_name || 'info';
            const source = event.hostname || event.source_ip;
            const message = event.message || '';
            const risk = event.risk_score || 0;

            row.innerHTML = `
                <div class="table-cell">${timestamp}</div>
                <div class="table-cell ${level}">${level}</div>
                <div class="table-cell primary">${source}</div>
                <div class="table-cell">${this.truncateText(message, 50)}</div>
                <div class="table-cell ${risk > 50 ? 'error' : 'success'}">${risk}</div>
            `;

            tableContainer.appendChild(row);
        });
    }

    updatePatternsChart(patterns) {
        if (this.charts.patterns && patterns && patterns.pattern_summary) {
            const entries = Object.entries(patterns.pattern_summary);
            const labels = entries.map(([key]) => key.replace(/_/g, ' '));
            const data = entries.map(([, value]) => Object.keys(value).length);

            this.charts.patterns.data.labels = labels.slice(0, 10);
            this.charts.patterns.data.datasets[0].data = data.slice(0, 10);
            this.charts.patterns.update('none');
        }
    }

    updatePerformanceStats(performance) {
        if (performance && performance.performance) {
            const perf = performance.performance;
            
            const elements = {
                'ingestion-rate': `${perf.current_eps || 0} EPS`,
                'storage-used': `${((perf.bytes_received || 0) / (1024**3)).toFixed(2)} GB`,
                'query-performance': `${(Math.random() * 100).toFixed(0)}ms` // Mock data
            };

            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            });
        }
    }

    async searchLogs() {
        const searchInput = document.getElementById('log-search');
        const query = searchInput ? searchInput.value : '';
        
        if (!query.trim()) {
            await this.loadLogStream();
            return;
        }

        try {
            const response = await fetch('/api/logs/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query: query,
                    range: this.timeRange,
                    limit: 100
                })
            });

            const results = await response.json();
            this.updateLogStream(results.logs || []);
            
        } catch (error) {
            console.error('Error searching logs:', error);
            this.showError('Search failed');
        }
    }

    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealtimeUpdate(data);
            };
            
            this.websocket.onclose = () => {
                // Reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    handleRealtimeUpdate(data) {
        if (data.type === 'new_log' && this.currentView === 'logs') {
            this.addLogEntryToStream(data.log);
        } else if (data.type === 'stats_update') {
            this.updateStatistics(data.stats);
        }
    }

    addLogEntryToStream(log) {
        const logContainer = document.getElementById('log-stream');
        if (!logContainer) return;

        const logEntry = this.createLogEntry(log);
        logContainer.insertBefore(logEntry, logContainer.firstChild);

        // Remove old entries if too many
        const entries = logContainer.children;
        if (entries.length > 200) {
            logContainer.removeChild(entries[entries.length - 1]);
        }
    }

    startAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }

        this.autoRefreshTimer = setInterval(() => {
            if (this.autoRefresh) {
                this.loadDashboardData();
            }
        }, this.refreshInterval);
    }

    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        const icon = document.getElementById('auto-refresh-icon');
        
        if (icon) {
            if (this.autoRefresh) {
                icon.classList.add('fa-spin');
            } else {
                icon.classList.remove('fa-spin');
            }
        }
    }

    // Utility functions
    animateValue(element, targetValue) {
        if (!element) return;
        
        const currentValue = parseInt(element.textContent) || 0;
        const increment = (targetValue - currentValue) / 20;
        let current = currentValue;
        
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= targetValue) || (increment < 0 && current <= targetValue)) {
                element.textContent = targetValue;
                clearInterval(timer);
            } else {
                element.textContent = Math.round(current);
            }
        }, 50);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    showError(message) {
        // Create a simple error notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--accent-red);
            color: white;
            padding: 1rem;
            border-radius: 6px;
            z-index: 10000;
            box-shadow: var(--shadow);
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Global functions for HTML event handlers
window.searchLogs = function() {
    window.dashboard.searchLogs();
};

window.clearSearch = function() {
    const searchInput = document.getElementById('log-search');
    if (searchInput) {
        searchInput.value = '';
        window.dashboard.loadLogStream();
    }
};

window.toggleAutoRefresh = function() {
    window.dashboard.toggleAutoRefresh();
};

window.exportLogs = function() {
    // Export current logs to CSV/JSON
    console.log('Export logs functionality');
};

window.toggleLogDetails = function() {
    // Toggle detailed log view
    console.log('Toggle log details functionality');
};

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new MarslogDashboard();
});
