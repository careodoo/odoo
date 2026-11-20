import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';

const _navy = Color(0xFF0A1F44);
const _sky = Color(0xFF0EA5E9);
const _muted = Color(0xFF64748B);
const _ink = Color(0xFF16203A);
const _bg = Color(0xFFEDF1F7);
const _ok = Color(0xFF16A34A);
const _crit = Color(0xFFDC2626);

Color _stC(String s) => s == 'approved' || s == 'converted'
    ? _ok
    : s == 'submitted'
        ? const Color(0xFF2563EB)
        : s == 'rejected'
            ? _crit
            : _muted;

/// 🚌 المواصلات — قائمة طلبات النقل بمشروع + إنشاء (مطابق لقسم البورتال).
class TransportScreen extends StatefulWidget {
  const TransportScreen({super.key});
  @override
  State<TransportScreen> createState() => _TransportScreenState();
}

class _TransportScreenState extends State<TransportScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _meta;
  int? _projectId;
  List _rows = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final m = await _api.trMeta();
      if (mounted) {
        setState(() {
          _meta = m;
          final ps = (m['projects'] as List?) ?? [];
          if (ps.isNotEmpty) _projectId = (ps.first as Map)['id'] as int;
        });
      }
      await _load();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.trList(projectId: _projectId);
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final projects = (_meta?['projects'] as List?) ?? [];
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _navy,
        foregroundColor: Colors.white,
        title: Text(tr('المواصلات', 'Transport')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      floatingActionButton: _projectId == null
          ? null
          : FloatingActionButton.extended(
              backgroundColor: _sky,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.directions_bus_rounded),
              label: Text(tr('طلب مواصلات', 'Request')),
              onPressed: _openCreate,
            ),
      body: Column(children: [
        if (projects.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
            child: DropdownButtonFormField<int>(
              value: _projectId,
              isExpanded: true,
              decoration: _dec(tr('المشروع', 'Project')),
              items: projects
                  .map((p) => DropdownMenuItem<int>(
                      value: (p as Map)['id'] as int, child: Text('${p['name']}', overflow: TextOverflow.ellipsis)))
                  .toList(),
              onChanged: (v) {
                setState(() => _projectId = v);
                _load();
              },
            ),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا طلبات مواصلات', 'No requests'), style: const TextStyle(color: _muted)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
                        itemCount: _rows.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _card(_rows[i] as Map),
                      ),
                    ),
        ),
      ]),
    );
  }

  Widget _card(Map t) {
    final st = (t['state'] ?? '').toString();
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(13),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
        leading: Container(
          width: 42, height: 42,
          decoration: BoxDecoration(color: _sky.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
          child: const Icon(Icons.directions_bus_rounded, color: _sky),
        ),
        title: Text('${t['name']} · ${t['kind_label']}', style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
        subtitle: Text('${t['route']}  ·  ${t['needed_date']}  ·  ${t['passengers']} ${tr('راكب', 'pax')}',
            style: const TextStyle(color: _muted, fontSize: 12)),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
          decoration: BoxDecoration(color: _stC(st).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(16)),
          child: Text('${t['state_label']}', style: TextStyle(color: _stC(st), fontWeight: FontWeight.w800, fontSize: 10.5)),
        ),
      ),
    );
  }

  Future<void> _openCreate() async {
    final ok = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => _TrCreate(meta: _meta!, projectId: _projectId!)));
    if (ok == true) _load();
  }

  InputDecoration _dec(String h) => InputDecoration(
      labelText: h, filled: true, fillColor: Colors.white, isDense: true,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)));
}

class _TrCreate extends StatefulWidget {
  final Map meta;
  final int projectId;
  const _TrCreate({required this.meta, required this.projectId});
  @override
  State<_TrCreate> createState() => _TrCreateState();
}

class _TrCreateState extends State<_TrCreate> {
  ApiClient get _api => context.read<AuthProvider>().api;
  String? _kind, _scope;
  int? _origin, _dest;
  final _pax = TextEditingController(text: '1');
  DateTime _date = DateTime.now();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final kinds = (widget.meta['kinds'] as List?) ?? [];
    final scopes = (widget.meta['scopes'] as List?) ?? [];
    if (kinds.isNotEmpty) _kind = (kinds.first as Map)['id'] as String;
    if (scopes.isNotEmpty) _scope = (scopes.first as Map)['id'] as String;
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      String d(DateTime x) => '${x.year}-${x.month.toString().padLeft(2, '0')}-${x.day.toString().padLeft(2, '0')}';
      await _api.trCreate({
        'project_id': widget.projectId,
        'transport_kind': _kind, 'trip_scope': _scope,
        'needed_date': d(_date),
        'passenger_count': int.tryParse(_pax.text) ?? 1,
        if (_origin != null) 'origin_location_id': _origin,
        if (_dest != null) 'destination_location_id': _dest,
        'submit': true,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('قُدّم طلب المواصلات', 'Submitted'))));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: _crit));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final kinds = (widget.meta['kinds'] as List?) ?? [];
    final scopes = (widget.meta['scopes'] as List?) ?? [];
    final locs = (widget.meta['locations'] as List?) ?? [];
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: _navy, foregroundColor: Colors.white, title: Text(tr('طلب مواصلات', 'Transport request'))),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: _sky, minimumSize: const Size.fromHeight(50)),
            onPressed: _busy ? null : _save,
            icon: const Icon(Icons.send_rounded),
            label: Text(tr('تقديم للاعتماد', 'Submit')),
          ),
        ),
      ),
      body: ListView(padding: const EdgeInsets.all(14), children: [
        _ddStr(tr('وسيلة النقل', 'Kind'), kinds, _kind, (v) => setState(() => _kind = v)),
        const SizedBox(height: 12),
        _ddStr(tr('نوع الرحلة', 'Scope'), scopes, _scope, (v) => setState(() => _scope = v)),
        const SizedBox(height: 12),
        _ddInt(tr('من موقع', 'From'), locs, _origin, (v) => setState(() => _origin = v)),
        const SizedBox(height: 12),
        _ddInt(tr('إلى موقع', 'To'), locs, _dest, (v) => setState(() => _dest = v)),
        const SizedBox(height: 12),
        InkWell(
          onTap: () async {
            final x = await showDatePicker(context: context, initialDate: _date, firstDate: DateTime(2024), lastDate: DateTime(2030));
            if (x != null) setState(() => _date = x);
          },
          child: InputDecorator(
            decoration: _dec(tr('تاريخ الحاجة', 'Date')),
            child: Text('${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        ),
        const SizedBox(height: 12),
        TextField(controller: _pax, keyboardType: TextInputType.number, decoration: _dec(tr('عدد الركّاب', 'Passengers'))),
      ]),
    );
  }

  Widget _ddStr(String label, List opts, String? val, ValueChanged<String?> onCh) => DropdownButtonFormField<String>(
        value: val, isExpanded: true, decoration: _dec(label),
        items: opts.map((o) => DropdownMenuItem<String>(value: (o as Map)['id'] as String, child: Text('${o['name']}'))).toList(),
        onChanged: onCh,
      );

  Widget _ddInt(String label, List opts, int? val, ValueChanged<int?> onCh) => DropdownButtonFormField<int>(
        value: val, isExpanded: true, decoration: _dec(label),
        items: opts.map((o) => DropdownMenuItem<int>(value: (o as Map)['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis))).toList(),
        onChanged: onCh,
      );

  InputDecoration _dec(String h) => InputDecoration(
      labelText: h, filled: true, fillColor: Colors.white, isDense: true,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)));
}
