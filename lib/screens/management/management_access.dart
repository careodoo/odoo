import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart' show RelationSearchSheet;

/// Managers configure per-user Management access: which systems show, and
/// whether add / edit / attachments / amounts are allowed.
class ManagementAccessScreen extends StatefulWidget {
  const ManagementAccessScreen({super.key});
  @override
  State<ManagementAccessScreen> createState() => _ManagementAccessScreenState();
}

class _ManagementAccessScreenState extends State<ManagementAccessScreen> {
  Map<String, dynamic>? _meta;
  bool _loading = true, _busy = false;
  String? _err;

  int? _userId;
  String? _userName;
  final Set<String> _hidden = {};
  final Set<String> _noCreate = {};
  final Set<String> _noEdit = {};
  bool _hideAttachments = false, _hideAmounts = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.managementAccessMeta();
      if (mounted) setState(() { _meta = m; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  Future<void> _pickUser() async {
    final picked = await showModalBottomSheet<Map>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => RelationSearchSheet(model: 'res.users', title: tr('اختر المستخدم', 'Select user'), accent: Mgmt.red),
    );
    if (picked == null || !mounted) return;
    setState(() { _userId = picked['v'] as int; _userName = '${picked['l']}'; _busy = true; });
    try {
      final cfg = await context.read<AuthProvider>().api.managementAccessGet(_userId!);
      if (!mounted) return;
      setState(() {
        _hidden..clear()..addAll(((cfg['hidden'] as List?) ?? const []).map((e) => '$e'));
        _noCreate..clear()..addAll(((cfg['no_create'] as List?) ?? const []).map((e) => '$e'));
        _noEdit..clear()..addAll(((cfg['no_edit'] as List?) ?? const []).map((e) => '$e'));
        _hideAttachments = cfg['hide_attachments'] == true;
        _hideAmounts = cfg['hide_amounts'] == true;
        _busy = false;
      });
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: Mgmt.red));

  Future<void> _save() async {
    if (_userId == null) { _snack(tr('اختر مستخدمًا أولًا', 'Select a user first')); return; }
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementAccessSave(_userId!, {
        'hidden': _hidden.toList(),
        'no_create': _noCreate.toList(),
        'no_edit': _noEdit.toList(),
        'hide_attachments': _hideAttachments,
        'hide_amounts': _hideAmounts,
      });
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ حُفظت صلاحيات $_userName', '✅ Saved for $_userName')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  @override
  Widget build(BuildContext context) {
    final systems = ((_meta?['systems'] as List?) ?? const []).cast<Map>();
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.red, foregroundColor: Colors.white, elevation: 0,
        title: Text('🔐 ${tr('صلاحيات الإدارة', 'Management access')}'),
      ),
      floatingActionButton: _userId == null ? null : FloatingActionButton.extended(
        backgroundColor: Mgmt.red, foregroundColor: Colors.white,
        onPressed: _busy ? null : _save,
        icon: const Icon(Icons.save_rounded),
        label: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _err != null
              ? Center(child: Padding(padding: const EdgeInsets.all(30), child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
              : Column(children: [
                  // user picker
                  Container(
                    color: Colors.white,
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12), onTap: _pickUser,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
                        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
                        child: Row(children: [
                          const Icon(Icons.person_rounded, color: Mgmt.red),
                          const SizedBox(width: 10),
                          Expanded(child: Text(_userName ?? tr('اختر المستخدم لضبط صلاحياته', 'Select a user to configure'),
                              maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _userName == null ? Mgmt.slate : Mgmt.ink))),
                          const Icon(Icons.expand_more_rounded, color: Mgmt.slate),
                        ]),
                      ),
                    ),
                  ),
                  if (_userId == null)
                    const Expanded(child: Center(child: Icon(Icons.admin_panel_settings_rounded, size: 90, color: Color(0xFFE2E8F0))))
                  else
                    Expanded(child: Stack(children: [
                      ListView(padding: const EdgeInsets.fromLTRB(12, 8, 12, 90), children: [
                        _globalCard(),
                        const SizedBox(height: 6),
                        Padding(padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
                            child: Text(tr('الأنظمة (${systems.length})', 'Systems (${systems.length})'),
                                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Mgmt.ink))),
                        for (final s in systems) _systemRow(s),
                      ]),
                      if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x11000000), child: Center(child: CircularProgressIndicator()))),
                    ])),
                ]),
    );
  }

  Widget _globalCard() => Container(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 6),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Column(children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero, dense: true,
            title: Text(tr('إخفاء المرفقات في كل السجلات', 'Hide attachments everywhere'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
            value: _hideAttachments, activeColor: Mgmt.red,
            onChanged: (v) => setState(() => _hideAttachments = v),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero, dense: true,
            title: Text(tr('إخفاء المبالغ المالية', 'Hide monetary amounts'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
            value: _hideAmounts, activeColor: Mgmt.red,
            onChanged: (v) => setState(() => _hideAmounts = v),
          ),
        ]),
      );

  Widget _systemRow(Map s) {
    final key = '${s['key']}';
    final visible = !_hidden.contains(key);
    Widget flag(String label, bool on, VoidCallback toggle, Color c) => Expanded(
          child: GestureDetector(
            onTap: visible ? toggle : null,
            child: Opacity(
              opacity: visible ? 1 : 0.35,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 3),
                padding: const EdgeInsets.symmetric(vertical: 7),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                    color: on ? c.withValues(alpha: 0.12) : Mgmt.bg,
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(color: on ? c.withValues(alpha: 0.4) : Colors.black12)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(on ? Icons.check_circle_rounded : Icons.remove_circle_outline_rounded, size: 13, color: on ? c : Mgmt.slate),
                  const SizedBox(width: 4),
                  Text(label, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: on ? c : Mgmt.slate)),
                ]),
              ),
            ),
          ),
        );
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.black12)),
      child: Column(children: [
        Row(children: [
          Text('${s['icon'] ?? ''} ', style: const TextStyle(fontSize: 16)),
          Expanded(child: Text(gLang == 'en' ? '${s['en']}' : '${s['ar']}',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
          // visible toggle
          Switch(
            value: visible, activeColor: const Color(0xFF16A34A),
            onChanged: (v) => setState(() => v ? _hidden.remove(key) : _hidden.add(key)),
          ),
        ]),
        const SizedBox(height: 2),
        Row(children: [
          flag(tr('إضافة', 'Add'), !_noCreate.contains(key), () => setState(() => _noCreate.contains(key) ? _noCreate.remove(key) : _noCreate.add(key)), const Color(0xFF2563EB)),
          flag(tr('تعديل', 'Edit'), !_noEdit.contains(key), () => setState(() => _noEdit.contains(key) ? _noEdit.remove(key) : _noEdit.add(key)), const Color(0xFF7C3AED)),
        ]),
      ]),
    );
  }
}
