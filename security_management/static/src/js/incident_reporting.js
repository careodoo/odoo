/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";

class IncidentReportingDashboard extends Component {
    setup() {
        this.state = useState({
            dashboardData: {},
            filters: {
                period: 'week',
                incident_type: 'all',
                severity: 'all'
            }
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.refreshInterval = null;
        
        onWillStart(async () => {
            await this.fetchDashboardData();
        });
        
        onMounted(() => {
            this.startAutoRefresh();
        });
        
        onWillUnmount(() => {
            this.stopAutoRefresh();
        });
    }
    
    async fetchDashboardData() {
        try {
            const result = await this.orm.call(
                "security.incidence.report",
                "get_dashboard_data",
                [[], this.state.filters]
            );
            this.state.dashboardData = result;
            // Initialize charts after data is loaded and DOM is updated
            setTimeout(() => this.initCharts(), 0);
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
        }
    }
    
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.onRefreshDashboard();
        }, 60000); // Refresh every minute
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    initCharts() {
        // Initialize incident type chart
        if (this.state.dashboardData.incident_stats) {
            const typeChartEl = document.querySelector('.o_incident_type_chart');
            if (typeChartEl) {
                const ctx = typeChartEl.getContext('2d');
                
                // Destroy previous chart if exists
                if (this.incidentTypeChart) {
                    this.incidentTypeChart.destroy();
                }
                
                const labels = [];
                const data = [];
                const backgroundColors = [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                    '#9966FF', '#FF9F40', '#8AC249', '#EA526F'
                ];
                
                let i = 0;
                Object.entries(this.state.dashboardData.incident_stats.by_type).forEach(([key, value]) => {
                    labels.push(key);
                    data.push(value);
                    i++;
                });
                
                this.incidentTypeChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColors.slice(0, i),
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                            },
                        },
                    }
                });
            }
        }

        // Initialize severity chart
        if (this.state.dashboardData.incident_stats) {
            const severityChartEl = document.querySelector('.o_incident_severity_chart');
            if (severityChartEl) {
                const ctx = severityChartEl.getContext('2d');
                
                // Destroy previous chart if exists
                if (this.severityChart) {
                    this.severityChart.destroy();
                }
                
                this.severityChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Low', 'Medium', 'High', 'Critical'],
                        datasets: [{
                            label: 'Incidents by Severity',
                            data: [
                                this.state.dashboardData.incident_stats.by_severity.low || 0,
                                this.state.dashboardData.incident_stats.by_severity.medium || 0,
                                this.state.dashboardData.incident_stats.by_severity.high || 0,
                                this.state.dashboardData.incident_stats.by_severity.critical || 0,
                            ],
                            backgroundColor: [
                                '#28a745', // green - low
                                '#ffc107', // yellow - medium
                                '#fd7e14', // orange - high
                                '#dc3545', // red - critical
                            ],
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1
                                }
                            }
                        }
                    }
                });
            }
        }

        // Initialize trend chart
        if (this.state.dashboardData.incident_stats && this.state.dashboardData.incident_stats.trend) {
            const trendChartEl = document.querySelector('.o_incident_trend_chart');
            if (trendChartEl) {
                const ctx = trendChartEl.getContext('2d');
                
                // Destroy previous chart if exists
                if (this.trendChart) {
                    this.trendChart.destroy();
                }
                
                const labels = [];
                const data = [];
                
                Object.entries(this.state.dashboardData.incident_stats.trend).forEach(([key, value]) => {
                    labels.push(key);
                    data.push(value);
                });
                
                this.trendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Incidents',
                            data: data,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: '#007bff',
                            pointRadius: 4,
                            fill: true,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1
                                }
                            }
                        }
                    }
                });
            }
        }
    }
    
    async onRefreshDashboard() {
        await this.fetchDashboardData();
    }
    
    onFilterChange(ev) {
        const filterName = ev.target.dataset.filter;
        const value = ev.target.value;
        this.state.filters[filterName] = value;
        this.onRefreshDashboard();
    }
    
    onIncidentCardClick(ev) {
        const incidentId = parseInt(ev.currentTarget.dataset.incidentId);
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.incidence.report',
            res_id: incidentId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    onCreateIncident() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.incidence.report',
            views: [[false, 'form']],
            target: 'current',
            context: {
                'form_view_initial_mode': 'edit',
            },
        });
    }
    
    onCreateInspection() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.inspection',
            views: [[false, 'form']],
            target: 'current',
            context: {
                'form_view_initial_mode': 'edit',
            },
        });
    }
}

IncidentReportingDashboard.template = 'security_management.IncidentReportingDashboard';

registry.category("actions").add("security_management.incident_reporting_dashboard", IncidentReportingDashboard);

export default IncidentReportingDashboard;
