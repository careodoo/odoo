/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const COLORS = {
    blue: "#3a7afe", green: "#21b07b", red: "#e25563", orange: "#f59e0b",
    purple: "#8b5cf6", teal: "#017e84", gray: "#9aa3b5", yellow: "#f1c40f",
};
const STATE_COLORS = {
    draft: COLORS.gray, submit: COLORS.blue, waiting: COLORS.orange, approve: COLORS.purple,
    won: COLORS.green, contracted: COLORS.teal, reject: COLORS.red, cancel: COLORS.gray,
};
const PALETTE = [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.teal, COLORS.yellow, COLORS.red, COLORS.gray];

export class ProposalDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ data: null, year: "all", loading: true });
        this.charts = {};
        this._pending = {};

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
        this.state.data = await this.orm.call("proposal.proposal", "get_dashboard_data", [this.state.year]);
        this.state.loading = false;
    }

    async onYearChange(ev) {
        this.state.year = ev.target.value;
        await this.loadData();
    }

    fmt(n) {
        if (n === null || n === undefined) return "0";
        const num = Number(n);
        if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(2) + "م";
        if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + "ألف";
        return num.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }

    openList(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "proposal.proposal",
            domain: domain || [],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    destroyCharts() {
        if (this._observer) { try { this._observer.disconnect(); } catch (e) { /* noop */ } this._observer = null; }
        this._pending = {};
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
        config.options = config.options || {};
        config.options.animation = false;
        config.options.responsive = true;
        config.options.resizeDelay = 200;
        this._pending[id] = config;
    }

    _create(id) {
        const config = this._pending[id];
        if (!config) return;
        delete this._pending[id];
        const ctx = this._ctx(id);
        if (!ctx) return;
        try {
            this.charts[id] = new Chart(ctx, config);
        } catch (e) {
            console.error("proposal dashboard: chart failed", id, e);
        }
    }

    _setupLazy() {
        const root = this.rootRef.el;
        if (!root) return;
        if (typeof IntersectionObserver === "undefined") {
            Object.keys(this._pending).forEach((id) => this._create(id));
            return;
        }
        const scroller = root.querySelector(".pd-scroll");
        this._observer = new IntersectionObserver(
            (entries) => {
                for (const e of entries) {
                    if (e.isIntersecting) {
                        const cv = e.target.querySelector("canvas");
                        if (cv) this._create(cv.id);
                        this._observer.unobserve(e.target);
                    }
                }
            },
            { root: scroller || null, rootMargin: "300px 0px" }
        );
        root.querySelectorAll(".chart").forEach((el) => this._observer.observe(el));
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
        let d;
        try { d = JSON.parse(JSON.stringify(this.state.data || {})); } catch (e) { d = this.state.data; }
        if (!d || !d.kpi) return;

        Chart.defaults.font.family = "'Cairo', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.animation = false;
        Chart.defaults.maintainAspectRatio = false;

        // status doughnut
        this._make("pdStatus", {
            type: "doughnut",
            data: {
                labels: d.status_dist.map((s) => s.label),
                datasets: [{
                    data: d.status_dist.map((s) => s.value),
                    backgroundColor: d.status_dist.map((s) => STATE_COLORS[s.key] || COLORS.gray),
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: { ...this._clickable((i) => { const s = d.status_dist[i]; this.openList([["state", "=", s.key]], s.label); }),
                maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } },
        });

        // monthly trend stacked bar
        this._make("pdTrend", {
            type: "bar",
            data: {
                labels: MONTHS,
                datasets: [
                    { label: "فائزة", data: d.trend.won, backgroundColor: COLORS.green, borderRadius: 4, stack: "s" },
                    { label: "خاسرة", data: d.trend.lost, backgroundColor: COLORS.red, borderRadius: 4, stack: "s" },
                    { label: "نشطة", data: d.trend.active, backgroundColor: COLORS.blue, borderRadius: 4, stack: "s" },
                ],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // value by service type (horizontal bar)
        this._make("pdService", {
            type: "bar",
            data: {
                labels: d.by_service.map((s) => s.label),
                datasets: [{ data: d.by_service.map((s) => s.value), backgroundColor: COLORS.teal, borderRadius: 4 }],
            },
            options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // pricing strategy (pie)
        this._make("pdStrategy", {
            type: "pie",
            data: {
                labels: d.strategy_dist.map((s) => s.label),
                datasets: [{ data: d.strategy_dist.map((s) => s.value), backgroundColor: PALETTE, borderWidth: 2, borderColor: "#fff" }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });

        // top customers (horizontal bar)
        this._make("pdCustomers", {
            type: "bar",
            data: {
                labels: d.top_customers.map((c) => c.name),
                datasets: [{ data: d.top_customers.map((c) => c.amount), backgroundColor: COLORS.blue, borderRadius: 4 }],
            },
            options: { ...this._clickable((i) => { const c = d.top_customers[i]; this.openList([["partner_id.name", "=", c.name]], c.name); }),
                indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // cumulative awarded value (line)
        this._make("pdCumval", {
            type: "line",
            data: {
                labels: MONTHS,
                datasets: [{ label: "تراكمي", data: d.cumulative, borderColor: COLORS.green,
                    backgroundColor: "rgba(33,176,123,.10)", fill: true, tension: 0.35, pointRadius: 3 }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } } },
        });

        // margin distribution (bar)
        this._make("pdMargin", {
            type: "bar",
            data: {
                labels: (d.margin_buckets || []).map((b) => b.label),
                datasets: [{ data: (d.margin_buckets || []).map((b) => b.value),
                    backgroundColor: [COLORS.red, COLORS.orange, COLORS.yellow, COLORS.blue, COLORS.green], borderRadius: 4 }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // avg margin by service type (horizontal bar)
        this._make("pdMarginSvc", {
            type: "bar",
            data: {
                labels: (d.avg_margin_service || []).map((s) => s.label),
                datasets: [{ data: (d.avg_margin_service || []).map((s) => s.value), backgroundColor: COLORS.purple, borderRadius: 4 }],
            },
            options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // by company (grouped bar: total vs won)
        this._make("pdCompany", {
            type: "bar",
            data: {
                labels: (d.by_company || []).map((c) => c.company),
                datasets: [
                    { label: "إجمالي", data: (d.by_company || []).map((c) => c.count), backgroundColor: COLORS.blue, borderRadius: 4 },
                    { label: "فائزة", data: (d.by_company || []).map((c) => c.won), backgroundColor: COLORS.green, borderRadius: 4 },
                ],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // service requests intake (doughnut)
        this._make("pdSr", {
            type: "doughnut",
            data: {
                labels: (d.sr_status || []).map((s) => s.label),
                datasets: [{ data: (d.sr_status || []).map((s) => s.value),
                    backgroundColor: [COLORS.gray, COLORS.orange, COLORS.green, COLORS.teal, COLORS.red], borderWidth: 2, borderColor: "#fff" }],
            },
            options: { maintainAspectRatio: false, cutout: "60%", plugins: { legend: { position: "bottom" } } },
        });

        this._setupLazy();
    }
}

ProposalDashboard.template = "care_proposal.ProposalDashboard";
registry.category("actions").add("proposal_dashboard", ProposalDashboard);
