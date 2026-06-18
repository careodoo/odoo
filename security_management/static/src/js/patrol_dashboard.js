/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";

class PatrolDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            dashboardData: {},
            currentPatrol: null
        });
        
        this.refreshInterval = null;
        this.completionChart = null;
        this.coverageChart = null;
        this.chartJSLoaded = false;
        
        onWillStart(async () => {
            await this.fetchDashboardData();
        });
        
        onMounted(() => {
            // Safely add class to o_content if it exists
            const contentElement = document.querySelector('.o_content');
            if (contentElement) {
                contentElement.classList.add('o_security_patrol_dashboard');
            }
            this.renderDashboard();
            this.startAutoRefresh();
        });
        
        onWillUnmount(() => {
            this.stopAutoRefresh();
        });
    }
    
    async fetchDashboardData() {
        try {
            const result = await this.orm.call(
                'security.patrol',
                'get_dashboard_data',
                [[]]
            );
            this.state.dashboardData = result;
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
        }
    }
    
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.refreshDashboard();
        }, 60000); // Refresh every minute
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    renderDashboard() {
        // The template will handle most of the rendering
        // This function is now mainly for initializing charts
        this.initCharts();
    }
    
    async initCharts() {
        // Load Chart.js if not already loaded
        if (!this.chartJSLoaded && !window.Chart) {
            try {
                await loadJS("https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js");
                this.chartJSLoaded = true;
            } catch (error) {
                console.error("Failed to load Chart.js:", error);
                this.notification.add(_t("Failed to load chart library. Please refresh the page."), {
                    title: _t("Error"),
                });
                return;
            }
        }
        
        if (this.state.dashboardData.patrol_stats) {
            const ctx = document.querySelector('.o_patrol_completion_chart')?.getContext('2d');
            if (!ctx) return;
            
            if (this.completionChart) {
                this.completionChart.destroy();
            }
            
            this.completionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: [
                        _t('Completed'),
                        _t('In Progress'),
                        _t('Scheduled'),
                        _t('Cancelled')
                    ],
                    datasets: [{
                        data: [
                            this.state.dashboardData.patrol_stats.completed || 0,
                            this.state.dashboardData.patrol_stats.in_progress || 0,
                            this.state.dashboardData.patrol_stats.scheduled || 0,
                            this.state.dashboardData.patrol_stats.cancelled || 0,
                        ],
                        backgroundColor: [
                            '#28a745',
                            '#007bff',
                            '#ffc107',
                            '#dc3545',
                        ],
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            padding: 10
                        }
                    },
                    layout: {
                        padding: 10
                    },
                    cutout: '65%'
                }
            });
        }
        
        if (this.state.dashboardData.point_coverage) {
            const ctx = document.querySelector('.o_point_coverage_chart')?.getContext('2d');
            if (!ctx) return;
            
            if (this.coverageChart) {
                this.coverageChart.destroy();
            }
            
            const labels = [];
            const data = [];
            
            Object.entries(this.state.dashboardData.point_coverage).forEach(([key, value]) => {
                labels.push(key);
                data.push(value);
            });
            
            this.coverageChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: _t('Points Covered'),
                        data: data,
                        backgroundColor: '#17a2b8',
                        barThickness: 'flex',
                        maxBarThickness: 50
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                padding: 15,
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            padding: 10
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                display: true,
                                drawBorder: true
                            },
                            ticks: {
                                padding: 5
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                padding: 5
                            }
                        }
                    },
                    layout: {
                        padding: 10
                    }
                }
            });
        }
    }
    
    async refreshDashboard() {
        await this.fetchDashboardData();
        this.renderDashboard();
    }
    
    onPatrolCardClick(ev) {
        const patrolId = ev.currentTarget.dataset.patrolId;
        
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.patrol',
            res_id: parseInt(patrolId),
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    async onStartPatrol(ev) {
        const patrolId = parseInt(ev.currentTarget.dataset.patrolId);
        
        try {
            await this.orm.call(
                'security.patrol',
                'action_start',
                [patrolId]
            );
            
            this.notification.add(_t("Patrol started successfully"), {
                title: _t("Success"),
            });
            
            await this.refreshDashboard();
        } catch (error) {
            this.notification.add(_t("Failed to start patrol: ") + error, {
                title: _t("Error"),
            });
        }
    }
    
    onScanPoint(ev) {
        const patrolId = parseInt(ev.currentTarget.dataset.patrolId);
        
        // Open the QR scanner for checkpoint scanning
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'security_manager.qr_scanner',
            target: 'new',
            context: {
                'default_patrol_id': patrolId,
                'scan_type': 'checkpoint',
            },
        });
    }
    
    async onCompletePatrol(ev) {
        const patrolId = parseInt(ev.currentTarget.dataset.patrolId);
        
        try {
            await this.orm.call(
                'security.patrol',
                'action_complete',
                [patrolId]
            );
            
            this.notification.add(_t("Patrol completed successfully"), {
                title: _t("Success"),
            });
            
            await this.refreshDashboard();
        } catch (error) {
            this.notification.add(_t("Failed to complete patrol: ") + error, {
                title: _t("Error"),
            });
        }
    }
}

PatrolDashboard.template = 'security_management.PatrolDashboard';
PatrolDashboard.props = {
    action: { type: Object, optional: true },
    actionId: { type: [Number, String], optional: true },
    className: { type: String, optional: true },
    globalState: { type: Object, optional: true },
    updateActionState: { type: Function, optional: true }
};

// Define services this component depends on
PatrolDashboard.services = {
    orm: "orm",
    action: "action",
    notification: "notification"
};

registry.category("actions").add("security_manager.patrol_dashboard", PatrolDashboard);

export default PatrolDashboard;
