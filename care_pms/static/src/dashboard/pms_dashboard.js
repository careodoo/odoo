/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const C = {
    blue: "#2f6df6", green: "#1a9f6d", red: "#e2513f", orange: "#e08a00",
    purple: "#7a5cf0", teal: "#017e84", gray: "#9aa3b5", navy: "#15213b",
};
const PALETTE = [C.blue, C.green, C.purple, C.orange, C.teal, C.red, C.navy, C.gray];

export class PmsDashboard extends Component {
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
        this.state.data = await this.orm.call("project.project", "get_pms_dashboard_data", []);
        this.state.loading = false;
    }

    fmt(n) { return Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

    openTasks(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window", name: name || "التاسكات",
            res_model: "project.task", domain: domain || [],
            views: [[false, "list"], [false, "kanban"], [false, "form"]], target: "current",
        });
    }
    openProjects(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window", name: name || "المشاريع",
            res_model: "project.project", domain: domain || [],
            views: [[false, "kanban"], [false, "list"], [false, "form"]], target: "current",
        });
    }

    destroyCharts() {
        for (const k of Object.keys(this.charts)) { try { this.charts[k].destroy(); } catch (e) { /* */ } }
        this.charts = {};
    }
    _ctx(id) { const el = this.rootRef.el && this.rootRef.el.querySelector("#" + id); return el ? el.getContext("2d") : null; }
    _make(id, config) {
        const ctx = this._ctx(id);
        if (!ctx) return;
        config.options = config.options || {};
        config.options.animation = false;
        config.options.maintainAspectRatio = false;
        try { this.charts[id] = new Chart(ctx, config); } catch (e) { console.error("pms dash", id, e); }
    }
    _clickable(handler) {
        return {
            onClick: (evt, els) => { if (els && els.length) handler(els[0].index); },
            onHover: (evt, els) => { const t = evt && evt.native && evt.native.target; if (t) t.style.cursor = els && els.length ? "pointer" : "default"; },
        };
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        this.destroyCharts();
        const d = this.state.data;
        if (!d) return;
        Chart.defaults.font.family = "'Cairo','Tahoma',sans-serif";
        Chart.defaults.animation = false;
        Chart.defaults.maintainAspectRatio = false;

        this._make("pmsKind", {
            type: "doughnut",
            data: {
                labels: d.by_kind.map((s) => s.label),
                datasets: [{ data: d.by_kind.map((s) => s.value), backgroundColor: PALETTE, borderWidth: 2, borderColor: "#fff" }],
            },
            options: { ...this._clickable((i) => { const s = d.by_kind[i]; this.openTasks([["task_kind", "=", s.key]], s.label); }),
                cutout: "60%", plugins: { legend: { position: "bottom" } } },
        });

        this._make("pmsCat", {
            type: "bar",
            data: {
                labels: d.by_cat.map((s) => s.label),
                datasets: [{ label: "متأخر", data: d.by_cat.map((s) => s.value), backgroundColor: C.red, borderRadius: 4 }],
            },
            options: { ...this._clickable((i) => { const s = d.by_cat[i]; this.openTasks([["pms_category_id", "=", s.id], ["is_overdue", "=", true]], s.label); }),
                indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } },
        });

        this._make("pmsDept", {
            type: "bar",
            data: {
                labels: d.by_dept.map((s) => s.label),
                datasets: [{ label: "متأخر", data: d.by_dept.map((s) => s.value), backgroundColor: C.orange, borderRadius: 4 }],
            },
            options: { ...this._clickable((i) => { const s = d.by_dept[i]; this.openTasks([["pms_department_id", "=", s.id], ["is_overdue", "=", true]], s.label); }),
                plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
        });
    }
}

PmsDashboard.template = "care_pms.PmsDashboard";
registry.category("actions").add("pms_dashboard", PmsDashboard);
