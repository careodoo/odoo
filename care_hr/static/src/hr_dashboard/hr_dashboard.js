/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const C = {
    blue: "#3a7afe", green: "#21b07b", red: "#e25563", orange: "#f59e0b",
    purple: "#8b5cf6", teal: "#017e84", gray: "#9aa3b5", pink: "#ec4899",
    cyan: "#06b6d4", odoo: "#714B67",
};
const PALETTE = [C.odoo, C.blue, C.green, C.orange, C.purple, C.teal, C.pink, C.cyan, C.red, C.gray];

export class HrDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ data: null, loading: true });
        this.charts = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        useEffect(
            () => {
                if (this.state.data && !this.state.loading) {
                    const h = setTimeout(() => this.renderCharts(), 60);
                    return () => clearTimeout(h);
                }
            },
            () => [this.state.data]
        );

        onWillUnmount(() => this.destroyCharts());
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call("hr.employee", "get_hr_dashboard_data", []);
        this.state.loading = false;
    }

    async refresh() {
        await this.loadData();
    }

    fmt(n) {
        const num = Number(n || 0);
        if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(2) + "م";
        if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + "ألف";
        return num.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }

    // open the employees list (optionally filtered) on KPI/chart click
    openEmployees(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "الموظفون",
            res_model: "hr.employee",
            domain: domain || [],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    // open any model list (used by the Care KPI row)
    openModel(model, domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || model,
            res_model: model,
            domain: domain || [],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    destroyCharts() {
        for (const k in this.charts) {
            try { this.charts[k].destroy(); } catch (e) { /* noop */ }
        }
        this.charts = {};
    }

    _ctx(id) {
        const root = this.rootRef.el;
        if (!root) return null;
        const el = root.querySelector(`#${id}`);
        return el ? el.getContext("2d") : null;
    }

    _make(id, config) {
        const ctx = this._ctx(id);
        if (!ctx) return;
        this.charts[id] = new Chart(ctx, config);
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        this.destroyCharts();
        // decouple from the OWL reactive proxy before handing arrays to Chart.js
        const d = JSON.parse(JSON.stringify(this.state.data));

        Chart.defaults.font.family = "'Cairo', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.animation = false;
        Chart.defaults.maintainAspectRatio = false;

        const noLegend = { plugins: { legend: { display: false } } };

        // headcount by department (vertical bars)
        this._make("hrByDept", {
            type: "bar",
            data: {
                labels: d.by_department.map((x) => x.name),
                datasets: [{ data: d.by_department.map((x) => x.count), backgroundColor: C.odoo, borderRadius: 6 }],
            },
            options: { ...noLegend, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
        });

        // skills by type (doughnut)
        if (d.by_skill_type && d.by_skill_type.length) {
            this._make("hrSkillType", {
                type: "doughnut",
                data: {
                    labels: d.by_skill_type.map((x) => x.name),
                    datasets: [{ data: d.by_skill_type.map((x) => x.count), backgroundColor: PALETTE }],
                },
                options: { plugins: { legend: { position: "bottom", labels: { font: { size: 10 } } } }, cutout: "55%" },
            });
        }
        // top skills (horizontal bars)
        if (d.top_skills && d.top_skills.length) {
            this._make("hrTopSkills", {
                type: "bar",
                data: {
                    labels: d.top_skills.map((x) => x.name),
                    datasets: [{ data: d.top_skills.map((x) => x.count), backgroundColor: C.purple, borderRadius: 6 }],
                },
                options: { ...noLegend, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
            });
        }

        // by nationality (horizontal bars)
        if (d.by_nationality && d.by_nationality.length) {
            this._make("hrByNat", {
                type: "bar",
                data: {
                    labels: d.by_nationality.map((x) => x.name),
                    datasets: [{ data: d.by_nationality.map((x) => x.count), backgroundColor: C.teal, borderRadius: 6 }],
                },
                options: { ...noLegend, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
            });
        }

        // by job (horizontal bars)
        this._make("hrByJob", {
            type: "bar",
            data: {
                labels: d.by_job.map((x) => x.name),
                datasets: [{ data: d.by_job.map((x) => x.count), backgroundColor: C.blue, borderRadius: 6 }],
            },
            options: { ...noLegend, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
        });

        // gender doughnut
        this._make("hrGender", {
            type: "doughnut",
            data: {
                labels: ["ذكور", "إناث", "أخرى"],
                datasets: [{
                    data: [d.by_gender.male, d.by_gender.female, d.by_gender.other],
                    backgroundColor: [C.blue, C.pink, C.gray],
                }],
            },
            options: { plugins: { legend: { position: "bottom" } }, cutout: "62%" },
        });

        // joiners trend (line, 12 months)
        this._make("hrJoiners", {
            type: "line",
            data: {
                labels: MONTHS,
                datasets: [{
                    data: d.joiners_trend, borderColor: C.green, backgroundColor: "rgba(33,176,123,.12)",
                    fill: true, tension: 0.35, pointRadius: 3,
                }],
            },
            options: { ...noLegend, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
        });

        // by category / tags
        if (d.by_category && d.by_category.length) {
            this._make("hrByCat", {
                type: "bar",
                data: {
                    labels: d.by_category.map((x) => x.name),
                    datasets: [{ data: d.by_category.map((x) => x.count), backgroundColor: PALETTE, borderRadius: 6 }],
                },
                options: { ...noLegend, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
            });
        }

        // leaves by type
        if (d.by_leave_type && d.by_leave_type.length) {
            this._make("hrLeaveType", {
                type: "bar",
                data: {
                    labels: d.by_leave_type.map((x) => x.name),
                    datasets: [{ data: d.by_leave_type.map((x) => x.count), backgroundColor: C.orange, borderRadius: 6 }],
                },
                options: { ...noLegend, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
            });
        }
    }
}

HrDashboard.template = "care_hr.HrDashboard";
registry.category("actions").add("care_hr_dashboard", HrDashboard);
