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
