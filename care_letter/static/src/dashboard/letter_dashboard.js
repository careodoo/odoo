/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const C = {
    blue: "#2f6df6", green: "#1a9f6d", red: "#e2513f", orange: "#e08a00",
    purple: "#7a5cf0", teal: "#017e84", gray: "#9aa3b5", yellow: "#f1c40f", navy: "#1e2a44",
};
const STATE_COLORS = {
    draft: C.gray, to_sign: C.orange, signed: C.blue, scanned: C.purple,
    with_delegate: C.orange, delivered: C.blue, acknowledged: C.green, archived: C.gray,
};
const PALETTE = [C.blue, C.green, C.purple, C.orange, C.teal, C.yellow, C.red, C.navy, C.gray];

export class LetterDashboard extends Component {
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
        this.state.data = await this.orm.call("letter.file", "get_dashboard_data", []);
        this.state.loading = false;
    }

    fmt(n) {
        const num = Number(n || 0);
        return num.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }

    openList(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "الكتب",
            res_model: "letter.file",
            domain: domain || [],
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            target: "current",
        });
    }

    destroyCharts() {
        for (const k of Object.keys(this.charts)) {
            try { this.charts[k].destroy(); } catch (e) { /* noop */ }
        }
        this.charts = {};
    }

    _ctx(id) {
        const el = this.rootRef.el && this.rootRef.el.querySelector("#" + id);
        return el ? el.getContext("2d") : null;
    }

    _make(id, config) {
        const ctx = this._ctx(id);
        if (!ctx) return;
        config.options = config.options || {};
        config.options.animation = false;
        config.options.maintainAspectRatio = false;
        try { this.charts[id] = new Chart(ctx, config); } catch (e) { console.error("letter dash", id, e); }
    }

    _clickable(handler) {
        return {
            onClick: (evt, els) => { if (els && els.length) handler(els[0].index); },
            onHover: (evt, els) => {
                const t = evt && evt.native && evt.native.target;
                if (t) t.style.cursor = els && els.length ? "pointer" : "default";
            },
        };
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        this.destroyCharts();
        const d = this.state.data;
        if (!d) return;

        Chart.defaults.font.family = "'Cairo','Tahoma',sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.animation = false;
        Chart.defaults.maintainAspectRatio = false;

        // status doughnut -> click opens that state
        this._make("ldStatus", {
            type: "doughnut",
            data: {
                labels: d.status_dist.map((s) => s.label),
                datasets: [{ data: d.status_dist.map((s) => s.value),
                    backgroundColor: d.status_dist.map((s) => STATE_COLORS[s.key] || C.gray),
                    borderWidth: 2, borderColor: "#fff" }],
            },
            options: { ...this._clickable((i) => { const s = d.status_dist[i]; this.openList([["letter_state", "=", s.key]], s.label); }),
                cutout: "60%", plugins: { legend: { position: "bottom" } } },
        });

        // direction pie
        this._make("ldDirection", {
            type: "pie",
            data: {
                labels: d.direction_dist.map((s) => s.label),
                datasets: [{ data: d.direction_dist.map((s) => s.value),
                    backgroundColor: [C.blue, C.orange, C.gray], borderWidth: 2, borderColor: "#fff" }],
            },
            options: { ...this._clickable((i) => { const s = d.direction_dist[i]; this.openList([["direction", "=", s.key]], s.label); }),
                plugins: { legend: { position: "bottom" } } },
        });

        // by classification bar
        this._make("ldClass", {
            type: "bar",
            data: {
                labels: d.by_class.map((s) => s.label),
                datasets: [{ data: d.by_class.map((s) => s.value), backgroundColor: C.teal, borderRadius: 4 }],
            },
            options: { ...this._clickable((i) => { const s = d.by_class[i]; this.openList([["classification_id", "=", s.id]], s.label); }),
                indexAxis: "y", plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // monthly trend bar
        this._make("ldTrend", {
            type: "bar",
            data: {
                labels: d.trend.labels,
                datasets: [{ label: "الكتب", data: d.trend.values, backgroundColor: C.blue, borderRadius: 4 }],
            },
            options: { plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // top partners horizontal bar -> click opens partner
        this._make("ldPartners", {
            type: "bar",
            data: {
                labels: d.top_partners.map((s) => s.name),
                datasets: [{ data: d.top_partners.map((s) => s.value), backgroundColor: C.purple, borderRadius: 4 }],
            },
            options: { ...this._clickable((i) => { const s = d.top_partners[i]; this.openList([["partner_id", "=", s.id]], s.name); }),
                indexAxis: "y", plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // OCR doughnut
        this._make("ldOcr", {
            type: "doughnut",
            data: {
                labels: d.ocr_dist.map((s) => s.label),
                datasets: [{ data: d.ocr_dist.map((s) => s.value),
                    backgroundColor: [C.gray, C.orange, C.green, C.red], borderWidth: 2, borderColor: "#fff" }],
            },
            options: { ...this._clickable((i) => { const s = d.ocr_dist[i]; this.openList([["ocr_state", "=", s.key]], s.label); }),
                cutout: "60%", plugins: { legend: { position: "bottom" } } },
        });

        // delegates grouped bar (total vs overdue) -> click opens delegate
        this._make("ldDelegates", {
            type: "bar",
            data: {
                labels: d.top_delegates.map((s) => s.name),
                datasets: [
                    { label: "إجمالي", data: d.top_delegates.map((s) => s.total), backgroundColor: C.blue, borderRadius: 4 },
                    { label: "متأخّر", data: d.top_delegates.map((s) => s.overdue), backgroundColor: C.red, borderRadius: 4 },
                ],
            },
            options: { ...this._clickable((i) => { const s = d.top_delegates[i]; this.openList([["delegate_id", "=", s.id]], s.name); }),
                plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });
    }
}

LetterDashboard.template = "care_letter.LetterDashboard";
registry.category("actions").add("letter_dashboard", LetterDashboard);
