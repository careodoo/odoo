/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const COLORS = {
    blue: "#3a7afe", green: "#21b07b", red: "#e25563", orange: "#f59e0b",
    purple: "#8b5cf6", teal: "#017e84", gray: "#9aa3b5", yellow: "#f1c40f", odoo: "#714B67",
};
const STATE_COLORS = {
    new: COLORS.gray, under_study: "#5b8cff", docs_purchased: COLORS.teal,
    interested: COLORS.purple, excepted: "#b0b7c3", preparing: COLORS.orange,
    participated: COLORS.blue, winner: COLORS.green, lost: COLORS.red,
    postponed: COLORS.orange, purchased: "#0bb6bd", in_progress: "#2b9a86",
    completed: "#6b7280", closed: COLORS.gray, cancelled: COLORS.red,
};

export class TenderDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ data: null, year: "all", loading: true });
        this.charts = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        useEffect(
            () => {
                if (this.state.data && !this.state.loading) {
                    // Defer so the KPIs/tables paint first; the page stays responsive
                    // even while charts initialize.
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
        this.state.data = await this.orm.call("purchase.tender", "get_dashboard_data", [this.state.year]);
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

    stateBadgeClass(key) {
        const map = {
            winner: "b-win", purchased: "b-win", in_progress: "b-win", completed: "b-new",
            lost: "b-lost", cancelled: "b-lost", excepted: "b-lost",
            participated: "b-part", docs_purchased: "b-part",
            interested: "b-int", under_study: "b-int",
            postponed: "b-post", preparing: "b-post",
            new: "b-new", closed: "b-new",
        };
        return map[key] || "b-new";
    }

    openTender(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "purchase.tender",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openList(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "purchase.tender",
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
        // Perf: no animations + debounce resize (avoid Chart.js ResizeObserver freeze).
        config.options.animation = false;
        config.options.responsive = true;
        config.options.resizeDelay = 200;
        this._pending[id] = config; // lazy: built only when scrolled into view
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
            console.error("tender dashboard: chart failed", id, e);
        }
    }

    _setupLazy() {
        const root = this.rootRef.el;
        if (!root) return;
        if (typeof IntersectionObserver === "undefined") {
            Object.keys(this._pending).forEach((id) => this._create(id));
            return;
        }
        const scroller = root.querySelector(".td-scroll");
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
        root.querySelectorAll(".chart, .chart-lg, .chart-sm").forEach((el) => this._observer.observe(el));
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        this.destroyCharts();
        // Decouple from the OWL reactive proxy: handing reactive arrays to Chart.js
        // can create a render/resize feedback loop that freezes the browser tab.
        let d;
        try { d = JSON.parse(JSON.stringify(this.state.data || {})); } catch (e) { d = this.state.data; }
        if (!d || !d.kpi) return;

        Chart.defaults.font.family = "'Cairo', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.animation = false;
        Chart.defaults.maintainAspectRatio = false;

        // monthly trend (stacked bar)
        this._make("tdTrend", {
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

        // status doughnut
        this._make("tdStatus", {
            type: "doughnut",
            data: {
                labels: d.status_dist.map((s) => s.label),
                datasets: [{
                    data: d.status_dist.map((s) => s.value),
                    backgroundColor: d.status_dist.map((s) => STATE_COLORS[s.key] || COLORS.gray),
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } },
        });

        // funnel (horizontal bar)
        this._make("tdFunnel", {
            type: "bar",
            data: {
                labels: ["مُدرَجة", "مُشارَك بها", "مؤهلة", "فائزة", "تم شراؤها"],
                datasets: [{
                    data: [d.funnel.listed, d.funnel.participated, d.funnel.qualified, d.funnel.won, d.funnel.purchased],
                    backgroundColor: [COLORS.gray, COLORS.blue, COLORS.purple, COLORS.green, COLORS.teal],
                    borderRadius: 4,
                }],
            },
            options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // cumulative value (line)
        this._make("tdCumval", {
            type: "line",
            data: {
                labels: MONTHS,
                datasets: [{
                    label: "تراكمي", data: d.cumulative, borderColor: COLORS.teal,
                    backgroundColor: "rgba(1,126,132,.10)", fill: true, tension: 0.35, pointRadius: 3,
                }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } } },
        });

        // top orgs (horizontal bar)
        this._make("tdOrgs", {
            type: "bar",
            data: {
                labels: d.top_orgs.map((o) => o.org),
                datasets: [{ data: d.top_orgs.map((o) => o.count), backgroundColor: COLORS.teal, borderRadius: 4 }],
            },
            options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        // bid type (pie)
        this._make("tdBidtype", {
            type: "pie",
            data: {
                labels: d.bid_dist.map((b) => b.label),
                datasets: [{
                    data: d.bid_dist.map((b) => b.value),
                    backgroundColor: [COLORS.blue, COLORS.purple, COLORS.orange, COLORS.gray, COLORS.teal, COLORS.yellow],
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });

        // rank distribution (bar)
        this._make("tdRank", {
            type: "bar",
            data: {
                labels: ["1", "2", "3", "4", "5+"],
                datasets: [{
                    data: ["1", "2", "3", "4", "5+"].map((k) => d.rank_dist[k] || 0),
                    backgroundColor: [COLORS.green, COLORS.orange, COLORS.yellow, COLORS.gray, COLORS.red],
                    borderRadius: 4,
                }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // by company (grouped bar: total vs won)
        this._make("tdCompany", {
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

        // by activity / bid type (pie)
        this._make("tdActivity", {
            type: "pie",
            data: {
                labels: (d.by_activity || []).map((a) => a.activity),
                datasets: [{
                    data: (d.by_activity || []).map((a) => a.count),
                    backgroundColor: [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.teal, COLORS.yellow, COLORS.red, COLORS.gray],
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });

        // forecast: weighted value by closing month (bar)
        this._make("tdForecast", {
            type: "bar",
            data: {
                labels: MONTHS,
                datasets: [{ label: "القيمة المرجّحة", data: d.forecast, backgroundColor: COLORS.green, borderRadius: 4 }],
            },
            options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
        });

        // loss reasons (doughnut)
        this._make("tdLoss", {
            type: "doughnut",
            data: {
                labels: (d.loss_reasons || []).map((x) => x.label),
                datasets: [{
                    data: (d.loss_reasons || []).map((x) => x.value),
                    backgroundColor: [COLORS.red, COLORS.orange, COLORS.purple, COLORS.gray, COLORS.blue, COLORS.teal, COLORS.yellow],
                    borderWidth: 2, borderColor: "#fff",
                }],
            },
            options: { cutout: "60%", maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });

        // competitors who beat us most (horizontal bar)
        this._make("tdCompBeat", {
            type: "bar",
            data: {
                labels: (d.comp_top || []).map((c) => c.name),
                datasets: [{ data: (d.comp_top || []).map((c) => c.value), backgroundColor: COLORS.red, borderRadius: 4 }],
            },
            options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });

        this._setupLazy();
    }
}

TenderDashboard.template = "purchase_tender.TenderDashboard";
registry.category("actions").add("purchase_tender_dashboard", TenderDashboard);
