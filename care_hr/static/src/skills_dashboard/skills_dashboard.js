/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const C = { navy: "#0f2b5b", blue: "#3a7afe", green: "#21b07b", red: "#e25563",
    orange: "#f59e0b", purple: "#8b5cf6", teal: "#017e84", cyan: "#06b6d4", gray: "#9aa3b5" };
const PALETTE = [C.navy, C.blue, C.green, C.orange, C.purple, C.teal, C.cyan, C.red, C.gray];

export class SkillsDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ data: null, loading: true });
        this.charts = {};
        onWillStart(async () => { await loadBundle("web.chartjs_lib"); await this.load(); });
        useEffect(() => {
            if (this.state.data && !this.state.loading) {
                const h = setTimeout(() => this.render2(), 60);
                return () => clearTimeout(h);
            }
        }, () => [this.state.data]);
        onWillUnmount(() => this.destroy2());
    }
    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("hr.employee.skill", "get_skills_dashboard_data", []);
        this.state.loading = false;
    }
    async refresh() { await this.load(); }
    fmt(n) {
        const v = Number(n || 0);
        if (Math.abs(v) >= 1000) return (v / 1000).toFixed(1) + "k";
        return v.toLocaleString("en-US", { maximumFractionDigits: 1 });
    }
    open(model, domain, name) {
        this.action.doAction({ type: "ir.actions.act_window", name, res_model: model,
            domain: domain || [], views: [[false, "list"], [false, "form"]], target: "current" });
    }
    openMatrix() {
        this.action.doAction({ type: "ir.actions.act_window", name: "Skills Matrix",
            res_model: "hr.employee.skill", views: [[false, "pivot"], [false, "graph"], [false, "list"]], target: "current" });
    }
    destroy2() { for (const k in this.charts) { try { this.charts[k].destroy(); } catch (e) {} } this.charts = {}; }
    _mk(id, cfg) {
        const root = this.rootRef.el; if (!root) return;
        const el = root.querySelector(`#${id}`); if (!el) return;
        this.charts[id] = new Chart(el.getContext("2d"), cfg);
    }
    render2() {
        if (typeof Chart === "undefined") return;
        this.destroy2();
        const d = JSON.parse(JSON.stringify(this.state.data));
        Chart.defaults.font.family = "'Cairo', sans-serif";
        Chart.defaults.animation = false; Chart.defaults.maintainAspectRatio = false;
        const noLeg = { plugins: { legend: { display: false } } };
        this._mk("skType", { type: "doughnut",
            data: { labels: d.by_type.map(x => x.name), datasets: [{ data: d.by_type.map(x => x.count), backgroundColor: PALETTE }] },
            options: { plugins: { legend: { position: "bottom", labels: { font: { size: 10 } } } }, cutout: "55%" } });
        this._mk("skTop", { type: "bar",
            data: { labels: d.top_skills.map(x => x.name), datasets: [{ data: d.top_skills.map(x => x.count), backgroundColor: C.purple, borderRadius: 6 }] },
            options: { ...noLeg, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } } });
        this._mk("skLang", { type: "bar",
            data: { labels: d.languages.map(x => x.name), datasets: [{ data: d.languages.map(x => x.count), backgroundColor: C.blue, borderRadius: 6 }] },
            options: { ...noLeg, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
        this._mk("skLevel", { type: "bar",
            data: { labels: d.levels.map(x => x.name), datasets: [{ data: d.levels.map(x => x.count), backgroundColor: C.teal, borderRadius: 6 }] },
            options: { ...noLeg, indexAxis: "y", scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } } });
    }
}
SkillsDashboard.template = "care_hr.SkillsDashboard";
registry.category("actions").add("care_skills_dashboard", SkillsDashboard);
