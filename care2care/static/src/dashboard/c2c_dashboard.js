/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class C2CDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: null, data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("c2c.booking", "get_app_dashboard", []);
            this.state.error = null;
        } catch (e) {
            this.state.error = (e && e.message && e.message.data && e.message.data.message) || "خطأ في التحميل";
        }
        this.state.loading = false;
    }

    get k() {
        return (this.state.data && this.state.data.kpis) || {};
    }
    get series() {
        const s = (this.state.data && this.state.data.series) || [];
        const max = Math.max(1, ...s.map((r) => r.value));
        return s.map((r) => ({ ...r, pct: Math.round((r.value / max) * 100) }));
    }
    get topServices() {
        const t = (this.state.data && this.state.data.top_services) || [];
        const max = Math.max(1, ...t.map((r) => r.count));
        return t.map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }));
    }
    stateColor(s) {
        const m = { draft: "#94a3b8", confirmed: "#3b82f6", assigned: "#6366f1", in_progress: "#f59e0b",
            done: "#16a34a", delivered: "#16a34a", converted: "#16a34a", cancelled: "#e11d48",
            quoted: "#8b5cf6", approved: "#16a34a", new: "#3b82f6", reviewing: "#f59e0b", shipped: "#0891b2" };
        return m[s] || "#64748b";
    }

    open(model, name, domain) {
        this.action.doAction({
            type: "ir.actions.act_window", name, res_model: model,
            views: [[false, "list"], [false, "form"]], domain: domain || [], target: "current",
        });
    }
    openRecord(model, id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: model, res_id: id,
            views: [[false, "form"]], target: "current",
        });
    }
    reload() { this.load(); }
}
C2CDashboard.template = "care2care.Dashboard";
registry.category("actions").add("c2c_dashboard", C2CDashboard);
