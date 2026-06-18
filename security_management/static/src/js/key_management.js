/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

class KeyManagementDashboard extends Component {
    setup() {
        this.state = useState({
            dashboardData: {},
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        
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
                "security.key",
                "get_dashboard_data",
                [[]]
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
        // Initialize key status chart
        if (this.state.dashboardData.key_stats) {
            const statusChartEl = document.querySelector('.o_key_status_chart');
            if (statusChartEl) {
                const ctx = statusChartEl.getContext('2d');
                
                // Destroy previous chart if exists
                if (this.keyStatusChart) {
                    this.keyStatusChart.destroy();
                }
                
                this.keyStatusChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Available', 'Checked Out', 'Lost', 'Maintenance'],
                        datasets: [{
                            data: [
                                this.state.dashboardData.key_stats.available || 0,
                                this.state.dashboardData.key_stats.checked_out || 0,
                                this.state.dashboardData.key_stats.lost || 0,
                                this.state.dashboardData.key_stats.maintenance || 0,
                            ],
                            backgroundColor: [
                                '#28a745', // green
                                '#007bff', // blue
                                '#dc3545', // red
                                '#ffc107', // yellow
                            ],
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

        // Initialize key usage chart
        if (this.state.dashboardData.key_usage) {
            const usageChartEl = document.querySelector('.o_key_usage_chart');
            if (usageChartEl) {
                const ctx = usageChartEl.getContext('2d');
                
                // Destroy previous chart if exists
                if (this.keyUsageChart) {
                    this.keyUsageChart.destroy();
                }
                
                const labels = [];
                const data = [];
                
                Object.entries(this.state.dashboardData.key_usage).forEach(([key, value]) => {
                    labels.push(key);
                    data.push(value);
                });
                
                this.keyUsageChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Usage Count',
                            data: data,
                            backgroundColor: '#17a2b8',
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
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
    
    onKeyCardClick(ev) {
        const keyId = parseInt(ev.currentTarget.dataset.keyId);
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.key',
            res_id: keyId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    onKeyHubCardClick(ev) {
        const hubId = parseInt(ev.currentTarget.dataset.hubId);
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.key.hub',
            res_id: hubId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    onKeyCheckout(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        const keyId = parseInt(ev.currentTarget.dataset.keyId);
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.key.checkout.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_key_id': keyId,
            },
        });
    }
    
    async onKeyCheckin(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        const keyId = parseInt(ev.currentTarget.dataset.keyId);
        
        const confirmed = await this.dialogService.add(Dialog, {
            title: "Confirmation",
            body: "Are you sure you want to check in this key?",
            confirmLabel: "Check In",
            cancelLabel: "Cancel",
        });
        
        if (confirmed) {
            try {
                await this.orm.call(
                    'security.key',
                    'action_checkin',
                    [[keyId]]
                );
                this.notification.add("Key checked in successfully", {
                    title: _t("Success"),
                });
                await this.onRefreshDashboard();
            } catch (error) {
                this.notification.add(`Failed to check in key: ${error}`, {
                    title: _t("Error"),
                });
            }
        }
    }
    
    onKeyReportLost(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        const keyId = parseInt(ev.currentTarget.dataset.keyId);
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'security.key.lost.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_key_id': keyId,
            },
        });
    }
}

KeyManagementDashboard.template = 'security_management.KeyManagementDashboard';

registry.category("actions").add("security_management.key_management_dashboard", KeyManagementDashboard);

export default KeyManagementDashboard;
