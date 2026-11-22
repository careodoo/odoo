/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { Component, onWillStart, useState } from "@odoo/owl";

const TABS = [
    ["overview", "نظرة عامة", "◆"],
    ["roles", "المسمّيات الوظيفية", "👤"],
    ["matrix", "مصفوفة الصلاحيات", "▦"],
    ["approvals", "توجيه الاعتمادات", "⇄"],
    ["notify", "الإشعارات", "🔔"],
    ["user", "بطاقة المستخدم", "🪪"],
    ["ideas", "أفكار متقدّمة", "✦"],
    ["migrate", "التوحيد والترحيل", "⇲"],
];
const LVLC = { "0": "v0", "1": "v1", "2": "v2" };
const LVLN = { "0": "—", "1": "قراءة", "2": "قراءة+كتابة" };

export class AccessConsole extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, error: null, tab: "overview",
            data: null, roleId: null, notifyMode: "admin", userId: null,
        });
        this.TABS = TABS;
        this.dir = (localization && localization.direction) || "ltr";
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const d = await this.orm.call("care.access.console", "get_data", []);
            this.state.data = d;
            if (d.roles.length && !this.state.roleId) {
                this.state.roleId = d.roles[0].id;
            }
            if (d.users && d.users.length && !this.state.userId) {
                this.state.userId = d.users[0].id;
            }
            this.state.error = null;
        } catch (e) {
            this.state.error = (e && e.message && e.message.data && e.message.data.message) || "خطأ في التحميل";
        }
        this.state.loading = false;
    }

    show(tab) { this.state.tab = tab; }

    rolesByTier(tierKey) {
        return (this.state.data.roles || []).filter((r) => r.tier === tierKey);
    }

    get currentRole() {
        return (this.state.data.roles || []).find((r) => r.id === this.state.roleId) || null;
    }
    get currentMatrix() {
        return (this.state.data.matrix[this.state.roleId] || []);
    }
    // group matrix rows by module
    get matrixGroups() {
        const rows = this.currentMatrix, out = [];
        let cur = null;
        for (const r of rows) {
            if (!cur || cur.module !== r.module) { cur = { module: r.module, rows: [] }; out.push(cur); }
            cur.rows.push(r);
        }
        return out;
    }
    lvlClass(l) { return LVLC[l] || "v0"; }
    lvlName(l) { return LVLN[l] || "—"; }

    pickRole(ev) { this.state.roleId = parseInt(ev.target.value); }
    openRoleMatrix(id) { this.state.roleId = id; this.state.tab = "matrix"; }

    async cycleLevel(line) {
        const next = String((parseInt(line.level) + 1) % 3);
        await this.orm.call("care.access.console", "set_level", [line.id, next]);
        line.level = next;
    }
    async setChannel(ch, value) {
        await this.orm.call("care.access.console", "set_channel", [ch.id, value]);
        ch.channel = value;
    }
    async toggleMandatory(ch) {
        ch.mandatory = await this.orm.call("care.access.console", "toggle_mandatory", [ch.id]);
    }
    async deriveAll() {
        await this.orm.call("care.access.console", "derive_all", []);
        this.notification.add("اشتُقّت مصفوفة كل المسمّيات من الوضع الحالي.", { type: "success" });
        await this.load();
        this.state.tab = "matrix";
    }
    async syncChannels() {
        const n = await this.orm.call("care.access.console", "sync_channels", []);
        this.notification.add("مزامنة الإشعارات: أُضيف " + n + " نوعًا.", { type: "success" });
        await this.load();
    }

    // ----- user card -----
    get currentUser() {
        return (this.state.data.users || []).find((u) => u.id === this.state.userId) || null;
    }
    pickUser(ev) { this.state.userId = parseInt(ev.target.value); }
    userHasRole(roleId) {
        const u = this.currentUser;
        return u && u.roles.indexOf(roleId) >= 0;
    }
    async toggleUserRole(roleId) {
        const u = this.currentUser;
        if (!u) return;
        const i = u.roles.indexOf(roleId);
        if (i >= 0) { u.roles.splice(i, 1); } else { u.roles.push(roleId); }
        await this.orm.call("care.access.console", "set_user_roles", [u.id, u.roles]);
    }
    userInitials(name) {
        const p = (name || "").trim().split(/\s+/);
        return ((p[0] || "")[0] || "") + (p.length > 1 ? "." + ((p[1] || "")[0] || "") : "");
    }
    get userUnionLevels() {
        // اتحاد مستويات مصفوفات مسمّيات المستخدم (الأعلى)، مجمّعة بالموديول
        const u = this.currentUser;
        if (!u) return [];
        const best = {};
        for (const rid of u.roles) {
            for (const line of (this.state.data.matrix[rid] || [])) {
                const k = line.model;
                if (!best[k] || parseInt(line.level) > parseInt(best[k].level)) {
                    best[k] = { module: line.module, label: line.label, level: line.level };
                }
            }
        }
        return Object.values(best).filter((x) => x.level !== "0");
    }

    // ----- ideas -----
    async toggleIdea(idea) {
        idea.on = await this.orm.call("care.access.console", "toggle_idea", [idea.key]);
    }
}
AccessConsole.template = "care_access_hub.Console";
registry.category("actions").add("care_access_console", AccessConsole);
