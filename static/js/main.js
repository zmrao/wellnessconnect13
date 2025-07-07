class DashboardManager {
    constructor() {
        this.apiBaseUrl = '/api';
        this.refreshInterval = 30000; // 30 seconds
        this.charts = {};
        this.currentView = 'overview';
        this.init();
    }

    init() {
        this.initializeDashboard();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    initializeDashboard() {
        try {
            this.loadLeadStats();
            this.loadAppointments();
            this.loadRecentActivity();
            this.setupCharts();
            this.updateLastRefresh();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to initialize dashboard');
        }
    }

    setupEventListeners() {
        // Navigation buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                this.switchView(view);
            });
        });

        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshDashboard();
            });
        }

        // Export button
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportReports();
            });
        }

        // Lead status filters
        document.querySelectorAll('.status-filter').forEach(filter => {
            filter.addEventListener('change', () => {
                this.filterLeads();
            });
        });

        // Appointment actions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('appointment-action')) {
                this.handleAppointmentAction(e.target);
            }
        });

        // Search functionality
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchLeads(e.target.value);
            });
        }
    }

    async loadLeadStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/leads/stats`);
            if (!response.ok) throw new Error('Failed to fetch lead stats');
            
            const stats = await response.json();
            this.updateLeadStats(stats);
        } catch (error) {
            console.error('Error loading lead stats:', error);
            this.showError('Failed to load lead statistics');
        }
    }

    updateLeadStats(stats) {
        const elements = {
            'total-leads': stats.total || 0,
            'qualified-leads': stats.qualified || 0,
            'pending-leads': stats.pending || 0,
            'converted-leads': stats.converted || 0,
            'conversion-rate': `${(stats.conversionRate || 0).toFixed(1)}%`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                element.classList.add('updated');
                setTimeout(() => element.classList.remove('updated'), 1000);
            }
        });

        this.updateLeadChart(stats);
    }

    async loadAppointments() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/appointments`);
            if (!response.ok) throw new Error('Failed to fetch appointments');
            
            const appointments = await response.json();
            this.displayAppointments(appointments);
        } catch (error) {
            console.error('Error loading appointments:', error);
            this.showError('Failed to load appointments');
        }
    }

    displayAppointments(appointments) {
        const container = document.getElementById('appointments-container');
        if (!container) return;

        if (appointments.length === 0) {
            container.innerHTML = '<div class="no-data">No appointments scheduled</div>';
            return;
        }

        const appointmentsHtml = appointments.map(apt => `
            <div class="appointment-card" data-id="${apt.id}">
                <div class="appointment-header">
                    <h4>${apt.client_name}</h4>
                    <span class="appointment-status status-${apt.status}">${apt.status}</span>
                </div>
                <div class="appointment-details">
                    <p><i class="icon-calendar"></i> ${this.formatDateTime(apt.scheduled_time)}</p>
                    <p><i class="icon-treatment"></i> ${apt.treatment_type}</p>
                    <p><i class="icon-phone"></i> ${apt.phone_number}</p>
                </div>
                <div class="appointment-actions">
                    <button class="btn btn-sm appointment-action" data-action="confirm" data-id="${apt.id}">Confirm</button>
                    <button class="btn btn-sm btn-secondary appointment-action" data-action="reschedule" data-id="${apt.id}">Reschedule</button>
                    <button class="btn btn-sm btn-danger appointment-action" data-action="cancel" data-id="${apt.id}">Cancel</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = appointmentsHtml;
    }

    handleAppointmentView(viewType = 'list') {
        const container = document.getElementById('appointments-view');
        if (!container) return;

        container.className = `appointments-view view-${viewType}`;
        
        if (viewType === 'calendar') {
            this.initializeCalendarView();
        } else {
            this.loadAppointments();
        }
    }

    async handleAppointmentAction(button) {
        const action = button.dataset.action;
        const appointmentId = button.dataset.id;

        try {
            button.disabled = true;
            button.textContent = 'Processing...';

            const response = await fetch(`${this.apiBaseUrl}/appointments/${appointmentId}/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error(`Failed to ${action} appointment`);

            const result = await response.json();
            this.showSuccess(`Appointment ${action}ed successfully`);
            this.loadAppointments(); // Refresh the list

        } catch (error) {
            console.error(`Error ${action}ing appointment:`, error);
            this.showError(`Failed to ${action} appointment`);
        } finally {
            button.disabled = false;
            button.textContent = action.charAt(0).toUpperCase() + action.slice(1);
        }
    }

    async loadRecentActivity() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/activity/recent`);
            if (!response.ok) throw new Error('Failed to fetch recent activity');
            
            const activities = await response.json();
            this.displayRecentActivity(activities);
        } catch (error) {
            console.error('Error loading recent activity:', error);
        }
    }

    displayRecentActivity(activities) {
        const container = document.getElementById('recent-activity');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = '<div class="no-data">No recent activity</div>';
            return;
        }

        const activitiesHtml = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    <i class="icon-${activity.type}"></i>
                </div>
                <div class="activity-content">
                    <p>${activity.description}</p>
                    <span class="activity-time">${this.formatRelativeTime(activity.timestamp)}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = activitiesHtml;
    }

    setupCharts() {
        this.initializeLeadChart();
        this.initializeTreatmentChart();
        this.initializeEngagementChart();
    }

    initializeLeadChart() {
        const canvas = document.getElementById('leads-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.leads = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Qualified', 'Pending', 'Converted', 'Unqualified'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#4CAF50', '#FF9800', '#2196F3', '#F44336'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    updateLeadChart(stats) {
        if (!this.charts.leads) return;

        this.charts.leads.data.datasets[0].data = [
            stats.qualified || 0,
            stats.pending || 0,
            stats.converted || 0,
            stats.unqualified || 0
        ];
        this.charts.leads.update();
    }

    initializeTreatmentChart() {
        const canvas = document.getElementById('treatment-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.treatments = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Blood Testing', 'PRP', 'Weight Management', 'Other'],
                datasets: [{
                    label: 'Appointments',
                    data: [0, 0, 0, 0],
                    backgroundColor: '#2196F3',
                    borderColor: '#1976D2',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    initializeEngagementChart() {
        const canvas = document.getElementById('engagement-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.charts.engagement = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages Sent',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Responses Received',
                    data: [],
                    borderColor: '#FF9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    switchView(viewName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.dashboard-section').forEach(section => {
            section.style.display = 'none';
        });
        
        const targetSection = document.getElementById(`${viewName}-section`);
        if (targetSection) {
            targetSection.style.display = 'block';
        }

        this.currentView = viewName;

        // Load view-specific data
        switch (viewName) {
            case 'appointments':
                this.handleAppointmentView();
                break;
            case 'leads':
                this.loadLeadDetails();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
        }
    }

    async loadLeadDetails() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/leads/detailed`);
            if (!response.ok) throw new Error('Failed to fetch lead details');
            
            const leads = await response.json();
            this.displayLeadDetails(leads);
        } catch (error) {
            console.error('Error loading lead details:', error);
            this.showError('Failed to load lead details');
        }
    }

    displayLeadDetails(leads) {
        const container = document.getElementById('leads-table-body');
        if (!container) return;

        if (leads.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="no-data">No leads found</td></tr>';
            return;
        }

        const leadsHtml = leads.map(lead => `
            <tr data-id="${lead.id}">
                <td>${lead.name || 'Unknown'}</td>
                <td>${lead.phone_number}</td>
                <td><span class="status-badge status-${lead.status}">${lead.status}</span></td>
                <td>${lead.treatment_type || 'Not specified'}</td>
                <td>${lead.urgency_score || 0}/10</td>
                <td>${this.formatDateTime(lead.created_at)}</td>
                <td>
                    <button class="btn btn-sm" onclick="dashboard.viewLeadDetails('${lead.id}')">View</button>
                </td>
            </tr>
        `).join('');

        container.innerHTML = leadsHtml;
    }

    async filterLeads() {
        const filters = {
            status: document.getElementById('status-filter')?.value || 'all',
            treatment: document.getElementById('treatment-filter')?.value || 'all',
            urgency: document.getElementById('urgency-filter')?.value || 'all'
        };

        try {
            const queryParams = new URLSearchParams();
            Object.entries(filters).forEach(([key, value]) => {
                if (value !== 'all') queryParams.append(key, value);
            });

            const response = await fetch(`${this.apiBaseUrl}/leads/detailed?${queryParams}`);
            if (!response.ok) throw new Error('Failed to filter leads');
            
            const leads = await response.json();
            this.displayLeadDetails(leads);
        } catch (error) {
            console.error('Error filtering leads:', error);
            this.showError('Failed to filter leads');
        }
    }

    async searchLeads(query) {
        if (query.length < 2) {
            this.loadLeadDetails();
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/leads/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Failed to search leads');
            
            const leads = await response.json();
            this.displayLeadDetails(leads);
        } catch (error) {
            console.error('Error searching leads:', error);
            this.showError('Failed to search leads');
        }
    }

    async exportReports() {
        try {
            const exportBtn = document.getElementById('export-btn');
            if (exportBtn) {
                exportBtn.disabled = true;
                exportBtn.textContent = 'Exporting...';
            }

            const response = await fetch(`${this.apiBaseUrl}/reports/export`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: 'comprehensive',
                    format: 'csv',
                    dateRange: this.getDateRange()
                })
            });

            if (!response.ok) throw new Error('Failed to export reports');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `wellness_report_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('Report exported successfully');

        } catch (error) {
            console.error('Error exporting reports:', error);
            this.showError('Failed to export reports');
        } finally {
            const exportBtn = document.getElementById('export-btn');
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.textContent = 'Export Reports';
            }
        }
    }

    refreshDashboard() {
        this.showLoading();
        this.initializeDashboard();
        setTimeout(() => this.hideLoading(), 1000);
    }

    startAutoRefresh() {
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadLeadStats();
                this.loadRecentActivity();
            }
        }, this.refreshInterval);
    }

    getDateRange() {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);
        
        return {
            start: startDate.toISOString().split('T')[0],
            end: endDate.toISOString().split('T')[0]
        };
    }

    formatDateTime(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatRelativeTime(timestamp) {
        if (!timestamp) return 'Unknown';
        const now = new Date();
        const date = new Date(timestamp);
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return this.formatDateTime(timestamp);
    }

    updateLastRefresh() {
        const element = document.getElementById('last-refresh');
        if (element) {
            element.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }
    }

    showLoading() {
        const loader = document.getElementById('loading-overlay');
        if (loader) loader.style.display = 'flex';
    }

    hideLoading() {
        const loader = document.getElementById('loading-overlay');
        if (loader) loader.style.display = 'none';
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);

        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();
});

// Global functions for inline event handlers
function initializeDashboard() {
    if (window.dashboard) {
        window.dashboard.initializeDashboard();
    }
}

function updateLeadStats(stats) {
    if (window.dashboard) {
        window.dashboard.updateLeadStats(stats);
    }
}

function handleAppointmentView(viewType) {
    if (window.dashboard) {
        window.dashboard.handleAppointmentView(viewType);
    }
}

function exportReports() {
    if (window.dashboard) {
        window.dashboard.exportReports();
    }
}