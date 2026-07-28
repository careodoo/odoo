/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class CafmDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: null, data: null, range: "month" });
        onWillStart(() => this.load());
    }

    setRange(r) {
        this.state.range = r;
    }

    get series() {
        const s = (this.state.data && this.state.data.series) || {};
        const rows = s[this.state.range] || [];
        const max = Math.max(1, ...rows.map((r) => r.value));
        return rows.map((r) => ({ ...r, pct: Math.round((r.value / max) * 100) }));
    }

    // conic-gradient donut من صفوف (label/pct/color)
    _donut(rows) {
        let acc = 0;
        const list = rows || [];
        const total = list.reduce((s, r) => s + (r.pct || 0), 0) || 100;
        const parts = list.map((r) => {
            const start = (acc / total) * 360;
            acc += r.pct || 0;
            const end = (acc / total) * 360;
            return `${r.color} ${start}deg ${end}deg`;
        });
        return `conic-gradient(${parts.join(",") || "#e2e8f0 0deg 360deg"})`;
    }
    get donutState() {
        return this._donut(this.state.data && this.state.data.by_state);
    }
    get donutService() {
        return this._donut(((this.state.data && this.state.data.by_service) || []).slice(0, 6));
    }
    get serviceLegend() {
        return ((this.state.data && this.state.data.by_service) || []).slice(0, 6);
    }

    // تنسيق مبلغ كبير: 1500000 -> 1.5M ، 12000 -> 12K
    money(v) {
        const n = Number(v) || 0;
        if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "M";
        if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(n % 1e3 ? 1 : 0) + "K";
        return String(Math.round(n));
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("care.cafm.workorder", "get_cafm_dashboard", []);
            this.state.error = null;
        } catch (e) {
            this.state.error = (e && e.message && e.message.data && e.message.data.message) || "خطأ في التحميل";
        }
        this.state.loading = false;
    }

    get k() {
        return (this.state.data && this.state.data.kpis) || {};
    }

    // open a work-order list filtered by domain
    openWO(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "أوامر العمل",
            res_model: "care.cafm.workorder",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
            target: "current",
        });
    }

    // فتح اختصار من الشريط العلوي: عبر إجراء القائمة إن وُجد، وإلا عبر الموديل
    openShortcut(sc) {
        if (sc.action_id) {
            this.action.doAction(sc.action_id);
        } else if (sc.model) {
            this.openModel(sc.model, sc.label);
        }
    }

    openModel(model, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openWORecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "care.cafm.workorder",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
CafmDashboard.template = "care_cafm.Dashboard";
registry.category("actions").add("care_cafm_dashboard", CafmDashboard);
