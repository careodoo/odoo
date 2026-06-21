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
const PALETTE = [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.teal, COLORS.yellow, COLORS.red, COLORS.gray];

export class CompetitorDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.state = useState({ data: null, competitor: "all", year: "all", loading: true });
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
        const comp = this.state.competitor === "all" ? null : parseInt(this.state.competitor);
        this.state.data = await this.orm.call("purchase.tender", "get_competitor_dashboard_data", [comp, this.state.year]);
        this.state.loading = false;
    }

    async onCompetitorChange(ev) {
        this.state.competitor = ev.target.value;
        await this.loadData();
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
        config.options.maintainAspectRatio = false;
        config.options.resizeDelay = 200;
        this._pending[id] = config;
    }

    _create(id) {
        const config = this._pending[id];
        if (!config) return;
        delete this._pending[id];
        const ctx = this._ctx(id);
        if (!ctx) return;
        try { this.charts[id] = new Chart(ctx, config); }
        catch (e) { console.error("competitor dashboard: chart failed", id, e); }
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

    _hbar(id, items, color) {
        this._make(id, {
            type: "bar",
            data: {
                labels: items.map((x) => x.name),
                datasets: [{ data: items.map((x) => x.value), backgroundColor: color, borderRadius: 4 }],
            },
            options: { indexAxis: "y", plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, grid: { display: false } } } },
        });
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

        if (d.mode === "all") {
            this._hbar("tdcThreats", d.top_threats || [], COLORS.red);
            this._hbar("tdcBeatUs", d.top_beat_us || [], COLORS.orange);
            this._hbar("tdcWins", d.top_wins || [], COLORS.green);
            this._hbar("tdcPriceIdx", d.price_index || [], COLORS.teal);
            this._hbar("tdcMinistry", (d.by_ministry || []).map((m) => ({ name: m.org, value: m.count })), COLORS.blue);
            this._make("tdcH2H", {
                type: "doughnut",
                data: {
                    labels: ["تغلّبنا عليهم", "تغلّبوا علينا"],
                    datasets: [{ data: [d.head_to_head.we_beat, d.head_to_head.they_beat],
                        backgroundColor: [COLORS.green, COLORS.red], borderWidth: 2, borderColor: "#fff" }],
                },
                options: { cutout: "60%", plugins: { legend: { position: "bottom" } } },
            });
        } else {
            this._make("tdcMonthly", {
                type: "bar",
                data: { labels: MONTHS, datasets: [{ label: "عطاءات", data: d.monthly, backgroundColor: COLORS.blue, borderRadius: 4 }] },
                options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
            });
            this._make("tdcPriceTrend", {
                type: "line",
                data: { labels: MONTHS, datasets: [{ label: "متوسط السعر", data: d.monthly_price,
                    borderColor: COLORS.teal, backgroundColor: "rgba(1,126,132,.10)", fill: true, tension: 0.35, pointRadius: 3 }] },
                options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
            });
            this._hbar("tdcMinistries", (d.ministries || []).map((m) => ({ name: m.org, value: m.count })), COLORS.teal);
            this._make("tdcH2H", {
                type: "doughnut",
                data: {
                    labels: ["تغلّبنا عليه", "تغلّب علينا"],
                    datasets: [{ data: [d.head_to_head.we_beat, d.head_to_head.they_beat],
                        backgroundColor: [COLORS.green, COLORS.red], borderWidth: 2, borderColor: "#fff" }],
                },
                options: { cutout: "60%", plugins: { legend: { position: "bottom" } } },
            });
        }

        this._setupLazy();
    }
}

CompetitorDashboard.template = "purchase_tender.CompetitorDashboard";
registry.category("actions").add("purchase_tender_competitor_dashboard", CompetitorDashboard);
