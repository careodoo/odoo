/** @odoo-module **/
// Approvals center tray in the system bar: fetches pending requests according to the user's permissions,
// approve/reject/view, updates automatically (without refresh) with an alert tone and a mute button.
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ApprovalCenterSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        let muted = false;
        try { muted = localStorage.getItem("ac_muted") === "1"; } catch (e) {}
        this.state = useState({
            open: false, loading: true, count: 0, items: [], chips: [],
            filter: "all", search: "", muted, user: { name: "", initials: "" },
            rejectKey: null, reason: "", leavingKey: null,
            detail: null, detailItem: null, detailLoading: false, detailReject: false,
        });
        this.knownKeys = new Set();
        this.first = true;
        this.audioCtx = null;

        onWillStart(() => this.load());
        this.timer = setInterval(() => this.load(true), 25000);
        onWillUnmount(() => clearInterval(this.timer));
    }

    // ===== Data fetching =====
    async load(isPoll) {
        let data;
        try { data = await this.rpc("/care_approval/data"); }
        catch (e) { this.state.loading = false; return; }
        const items = [];
        const chips = [];
        (data.groups || []).forEach((g) => {
            chips.push({ key: g.key, module: g.module, icon: g.icon, count: g.count });
            g.records.forEach((r) => {
                const uid = r.model + ":" + r.id;
                items.push(Object.assign({}, r, {
                    uid, module: g.module, icon: g.icon, color: g.color,
                    fresh: !this.first && !this.knownKeys.has(uid),
                }));
            });
        });
        // Detect new requests → sound. نجمع العناصر الجديدة فعليًّا لعرض بياناتها في الإشعار.
        const keys = new Set(items.map((i) => i.uid));
        const freshItems = this.first ? [] : items.filter((i) => !this.knownKeys.has(i.uid));
        this.knownKeys = keys;
        this.first = false;

        this.state.items = items;
        this.state.chips = chips;
        this.state.count = data.count || 0;
        this.state.user = data.user || this.state.user;
        this.state.loading = false;
        if (this.state.filter !== "all" && !chips.some((c) => c.key === this.state.filter)) {
            this.state.filter = "all";
        }
        if (freshItems.length) {
            this.chime();
            if (!this.state.open) {
                this.notifyFresh(freshItems);
            }
        }
    }

    // إشعار غنيّ ببيانات الطلب (بدل النص العام): المرجع + الموضوع + أهمّ الحقول (مُقدّم الطلب/النوع/المبلغ…)
    notifyFresh(freshItems) {
        const summarize = (it) => {
            const head = [it.ref, it.subject || it.title].filter(Boolean).join(" — ");
            const extra = [];
            if (it.by) { extra.push(`${it.by_role || "مُقدّم الطلب"}: ${it.by}`); }
            (it.fields || []).forEach((f) => {
                if (Array.isArray(f) && f[1]) { extra.push(`${f[0]}: ${f[1]}`); }
            });
            const tail = extra.slice(0, 3).join(" · ");
            return tail ? `${head} · ${tail}` : head;
        };
        let title, body;
        if (freshItems.length === 1) {
            const it = freshItems[0];
            title = it.title ? `مركز الموافقات · ${it.title}` : "مركز الموافقات";
            body = summarize(it) || "لديك طلب جديد بانتظار موافقتك";
        } else {
            title = `مركز الموافقات · ${freshItems.length} طلبات جديدة`;
            body = freshItems.slice(0, 4).map((it) =>
                "• " + ([it.ref, it.subject || it.title].filter(Boolean).join(" — ") || "طلب")
            ).join("\n");
            if (freshItems.length > 4) body += `\n… و${freshItems.length - 4} أخرى`;
        }
        this.notification.add(body, { type: "info", title });
    }

    get visibleItems() {
        let items = this.state.items;
        if (this.state.filter !== "all") {
            items = items.filter((i) => this._modKey(i) === this.state.filter);
        }
        const q = (this.state.search || "").trim().toLowerCase();
        if (q) {
            items = items.filter((i) => this._searchBlob(i).includes(q));
        }
        return items;
    }
    // Searchable text: the reference + the title + the subject + the worker badge + the field values (worker/department/project/number)
    _searchBlob(item) {
        const parts = [item.ref, item.title, item.subject, item.badge];
        (item.fields || []).forEach((f) => { if (Array.isArray(f)) { parts.push(f[1]); } });
        return parts.filter(Boolean).join(" ").toLowerCase();
    }
    clearSearch() { this.state.search = ""; }
    _modKey(item) {
        const c = this.state.chips.find((c) => c.module === item.module);
        return c ? c.key : "";
    }

    // ===== Interaction =====
    toggle() { this.state.open = !this.state.open; if (this.state.open) { this.ensureAudio(); this.load(); } }
    close() { this.state.open = false; this.state.rejectKey = null; }
    setFilter(k) { this.state.filter = k; }
    askReject(r) { this.state.rejectKey = r.uid; this.state.reason = ""; }
    cancelReject() { this.state.rejectKey = null; this.state.reason = ""; }

    async decide(r, approve) {
        const reason = approve ? "" : (this.state.reason || "");
        this.state.leavingKey = r.uid;          // حركة الاختفاء
        this.state.rejectKey = null;
        await new Promise((res) => setTimeout(res, 300));
        let out;
        try {
            out = await this.rpc("/care_approval/decide", {
                model: r.model, res_id: r.id, approve, reason,
            });
        } catch (e) { out = { ok: false, error: String(e) }; }
        this.state.leavingKey = null;
        this.state.reason = "";
        if (out && out.ok) {
            this.notification.add(
                approve ? `تم اعتماد «${r.ref}»` : `تم رفض «${r.ref}»`,
                { type: approve ? "success" : "warning" });
            this.knownKeys.delete(r.uid);
        } else {
            this.notification.add(out && out.error ? out.error : "تعذّر تنفيذ القرار", { type: "danger" });
        }
        await this.load();
    }

    // ===== Full details dialog =====
    async openDetail(r) {
        this.state.detailItem = r;
        this.state.detail = null;
        this.state.detailLoading = true;
        this.state.detailReject = false;
        this.state.reason = "";
        let d;
        try { d = await this.rpc("/care_approval/detail", { model: r.model, res_id: r.id }); }
        catch (e) { d = { error: String(e) }; }
        this.state.detail = d;
        this.state.detailLoading = false;
    }
    closeDetail() {
        this.state.detail = null; this.state.detailItem = null;
        this.state.detailReject = false; this.state.reason = "";
    }
    askRejectDetail() { this.state.detailReject = true; this.state.reason = ""; }
    cancelRejectDetail() { this.state.detailReject = false; this.state.reason = ""; }
    async decideDetail(approve) {
        const r = this.state.detailItem;
        if (!r) return;
        const reason = approve ? "" : (this.state.reason || "");
        this.closeDetail();
        this.state.reason = reason;   // decide() يقرأ السبب من الحالة
        await this.decide(r, approve);
    }
    openRecordDetail() {
        const r = this.state.detailItem;
        this.closeDetail();
        if (r) this.openRecord(r);
    }

    openRecord(r) {
        this.state.open = false;
        this.action.doAction({
            type: "ir.actions.act_window", res_model: r.model, res_id: r.id,
            views: [[false, "form"]], target: "current",
        });
    }
    openLog() {
        this.state.open = false;
        this.action.doAction("care_approval_center.action_approval_log");
    }

    // ===== Sound =====
    ensureAudio() {
        try {
            if (!this.audioCtx) this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (this.audioCtx.state === "suspended") this.audioCtx.resume();
        } catch (e) {}
    }
    chime() {
        if (this.state.muted) return;
        this.ensureAudio();
        const ctx = this.audioCtx;
        if (!ctx) return;
        const t = ctx.currentTime;
        [[880, 0], [1174.66, 0.11], [1567.98, 0.22]].forEach(([f, dly]) => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.type = "sine"; o.frequency.value = f; o.connect(g); g.connect(ctx.destination);
            g.gain.setValueAtTime(0.0001, t + dly);
            g.gain.exponentialRampToValueAtTime(0.2, t + dly + 0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, t + dly + 0.5);
            o.start(t + dly); o.stop(t + dly + 0.55);
        });
    }
    toggleMute() {
        this.state.muted = !this.state.muted;
        try { localStorage.setItem("ac_muted", this.state.muted ? "1" : "0"); } catch (e) {}
        if (!this.state.muted) { this.ensureAudio(); this.chime(); }
    }
}
ApprovalCenterSystray.template = "care_approval_center.Systray";

registry.category("systray").add(
    "care_approval_center.ApprovalCenter",
    { Component: ApprovalCenterSystray },
    { sequence: 20 }
);
