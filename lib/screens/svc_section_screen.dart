import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/record_report.dart';

/// Any service section, from the backend's own declaration.
///
/// The app used to show these services as filtered work orders — the real
/// records (pool readings, tank cleanings, pest stations, disinfection rounds)
/// lived only in Odoo. The registry describes 39 sections across 11 services,
/// so one screen renders them all: a section added on the server appears here
/// with no Dart written for it.
class SvcSectionScreen extends StatefulWidget {
  const SvcSectionScreen({
    super.key,
    required this.code,
    required this.sectionKey,
    required this.title,
    this.accent = const Color(0xFF0D9488),
  });

  final String code;
  final String sectionKey;
  final String title;
  final Color accent;

  @override
  State<SvcSectionScreen> createState() => _SvcSectionScreenState();
}

class _SvcSectionScreenState extends State<SvcSectionScreen> {
  Map<String, dynamic>? _d;
  String? _error;
  int _page = 1;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final d = await context
          .read<AuthProvider>()
          .api
          .svcSection(widget.code, widget.sectionKey, page: _page);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  List<Map> get _rows => ((_d?['rows'] as List?) ?? const []).cast<Map>();
  bool get _canAdd => _d?['can_add'] == true;
  bool get _canCancel => _d?['can_cancel'] == true;

  static const _pillColors = {
    'ok': Color(0xFF16A34A),
    'warn': Color(0xFFF59E0B),
    'danger': Color(0xFFE11D48),
    'info': Color(0xFF3B82F6),
    'muted': Color(0xFF64748B),
  };

  @override
  Widget build(BuildContext context) {
    final total = intOf(_d?['total'], 0);
    final pages = intOf(_d?['pages'], 1);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: widget.accent,
        foregroundColor: Colors.white,
        title: Text(widget.title,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)],
      ),
      floatingActionButton: _canAdd
          ? FloatingActionButton.extended(
              backgroundColor: widget.accent,
              onPressed: _busy ? null : _addSheet,
              icon: const Icon(Icons.add_rounded),
              label: Text('${_d?['add_label'] ?? tr('إضافة', 'Add')}',
                  style: const TextStyle(fontWeight: FontWeight.w900)),
            )
          : null,
      body: _d == null
          ? Center(
              child: _error != null
                  ? Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(_error!,
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey.shade600)))
                  : CircularProgressIndicator(color: widget.accent))
          : RefreshIndicator(
              color: widget.accent,
              onRefresh: _load,
              child: _rows.isEmpty
                  ? ListView(children: [
                      const SizedBox(height: 90),
                      Icon(Icons.inbox_rounded,
                          size: 54, color: Colors.grey.shade300),
                      const SizedBox(height: 12),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 32),
                        child: Text(
                            '${(_d?['section'] as Map?)?['empty'] ?? tr('لا توجد سجلات', 'No records')}',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: Colors.grey.shade600,
                                fontWeight: FontWeight.w600)),
                      ),
                    ])
                  : ListView(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10, right: 4),
                          child: Text(
                              '${tr('السجلات', 'Records')}: $total',
                              style: TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.grey.shade600)),
                        ),
                        for (final r in _rows) _card(r),
                        if (pages > 1) _pager(pages),
                      ],
                    ),
            ),
    );
  }

  Widget _card(Map r) {
    final pills = ((r['pills'] as List?) ?? const []).cast<Map>();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${r['title'] ?? ''}',
            style: const TextStyle(
                fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF14202B))),
        if ('${r['subtitle'] ?? ''}'.isNotEmpty) ...[
          const SizedBox(height: 3),
          Text('${r['subtitle']}',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
        ],
        if (pills.isNotEmpty) ...[
          const SizedBox(height: 9),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final p in pills)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                    color: (_pillColors['${p['c']}'] ?? _pillColors['info']!)
                        .withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20)),
                child: Text('${p['t']}',
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: _pillColors['${p['c']}'] ?? _pillColors['info']!)),
              ),
          ]),
        ],
        const SizedBox(height: 10),
        Row(children: [
          _smallBtn(Icons.picture_as_pdf_outlined, tr('تقرير', 'Report'),
              const Color(0xFF64748B), () {
            final model = '${(_d?['section'] as Map?)?['model'] ?? ''}'
                .replaceAll('.', '_');
            if (model.isEmpty) return;
            openRecordReport(context,
                code: model, id: (r['id'] as num).toInt(), title: '${r['title']}');
          }),
          if (_canCancel) ...[
            const SizedBox(width: 8),
            _smallBtn(Icons.delete_outline_rounded, tr('إلغاء', 'Cancel'),
                const Color(0xFFE11D48),
                () => _confirmCancel((r['id'] as num).toInt(), '${r['title']}')),
          ],
        ]),
      ]),
    );
  }

  Widget _smallBtn(IconData ic, String label, Color c, VoidCallback onTap) =>
      OutlinedButton.icon(
        onPressed: _busy ? null : onTap,
        icon: Icon(ic, size: 15),
        style: OutlinedButton.styleFrom(
          foregroundColor: c,
          side: BorderSide(color: c.withValues(alpha: 0.4)),
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        label: Text(label,
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
      );

  Widget _pager(int pages) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Wrap(
          alignment: WrapAlignment.center,
          spacing: 7,
          children: [
            for (var i = 1; i <= pages; i++)
              ChoiceChip(
                label: Text('$i'),
                selected: i == _page,
                selectedColor: widget.accent,
                labelStyle: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                    color: i == _page ? Colors.white : Colors.grey.shade700),
                onSelected: (_) {
                  setState(() { _page = i; _d = null; });
                  _load();
                },
              ),
          ],
        ),
      );

  /// Cancelling names what will happen — the server picks the least
  /// destructive path (cancel state, else archive, else delete).
  Future<void> _confirmCancel(int id, String title) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(tr('إلغاء السجل', 'Cancel record'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: Text(
            tr('سيُلغى «$title» — إن كانت له حالة إلغاء تُستخدم، وإلا يُؤرشف.',
               '"$title" will be cancelled, or archived if it has no cancel state.'),
            style: const TextStyle(fontSize: 13.5)),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: Text(tr('تراجع', 'Back'))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE11D48)),
              onPressed: () => Navigator.pop(c, true),
              child: Text(tr('إلغاء السجل', 'Cancel it'))),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context
          .read<AuthProvider>()
          .api
          .svcCancel(widget.code, widget.sectionKey, id);
      if (!mounted) return;
      _snack(tr('تم الإلغاء', 'Cancelled'), const Color(0xFF16A34A));
      await _load();
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// The add form is built from the field list the server sends, so a new
  /// field on a section appears here without this file changing.
  Future<void> _addSheet() async {
    final fields = ((_d?['fields'] as List?) ?? const []).cast<Map>();
    if (fields.isEmpty) {
      _snack(tr('لا توجد حقول للإضافة', 'Nothing to add'), widget.accent);
      return;
    }
    final values = <String, dynamic>{
      for (final f in fields)
        if (f['default'] != null) '${f['name']}': f['default'],
    };
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _AddSheet(
          fields: fields,
          values: values,
          accent: widget.accent,
          title: '${_d?['add_label'] ?? tr('إضافة سجل', 'Add record')}',
          onSave: () => context
              .read<AuthProvider>()
              .api
              .svcAdd(widget.code, widget.sectionKey, values)),
    );
    if (saved == true && mounted) {
      _snack(tr('تم الحفظ', 'Saved'), const Color(0xFF16A34A));
      setState(() { _page = 1; _d = null; });
      await _load();
    }
  }

  void _snack(String m, Color c) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));
}

class _AddSheet extends StatefulWidget {
  const _AddSheet({
    required this.fields,
    required this.values,
    required this.accent,
    required this.title,
    required this.onSave,
  });

  final List<Map> fields;
  final Map<String, dynamic> values;
  final Color accent;
  final String title;
  final Future<Map<String, dynamic>> Function() onSave;

  @override
  State<_AddSheet> createState() => _AddSheetState();
}

class _AddSheetState extends State<_AddSheet> {
  bool _saving = false;

  Future<void> _save() async {
    for (final f in widget.fields) {
      if (f['required'] == true) {
        final v = widget.values['${f['name']}'];
        if (v == null || '$v'.trim().isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
              content: Text('${tr('أكمل', 'Required')}: ${f['label']}'),
              backgroundColor: widget.accent,
              behavior: SnackBarBehavior.floating));
          return;
        }
      }
    }
    setState(() => _saving = true);
    try {
      await widget.onSave();
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('$e'),
            backgroundColor: const Color(0xFFE11D48),
            behavior: SnackBarBehavior.floating));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(
            color: Color(0xFFF6F7F9),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 12, 12, 14),
            color: widget.accent,
            child: Row(children: [
              Expanded(
                  child: Text(widget.title,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16.5,
                          fontWeight: FontWeight.w900))),
              IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.white),
                  onPressed: () => Navigator.pop(context)),
            ]),
          ),
          Expanded(
            child: ListView(
              controller: sc,
              padding: const EdgeInsets.all(16),
              children: [for (final f in widget.fields) _field(f)],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: SizedBox(
                height: 50,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                      backgroundColor: widget.accent,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14))),
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox(
                          width: 17,
                          height: 17,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.check_rounded),
                  label: Text(tr('حفظ', 'Save'),
                      style: const TextStyle(
                          fontWeight: FontWeight.w900, fontSize: 15)),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _field(Map f) {
    final name = '${f['name']}';
    final kind = '${f['kind']}';
    final label =
        '${f['label']}${f['required'] == true ? ' *' : ''}';
    final opts = ((f['options'] as List?) ?? const []).cast<Map>();

    Widget input;
    if (kind == 'bool') {
      input = SwitchListTile(
        value: widget.values[name] == true,
        onChanged: (v) => setState(() => widget.values[name] = v),
        activeThumbColor: widget.accent,
        contentPadding: EdgeInsets.zero,
        title: Text(label,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );
      return Padding(padding: const EdgeInsets.only(bottom: 6), child: input);
    } else if (kind == 'm2o' || kind == 'select') {
      final vals = opts.map((o) => '${o['v']}').toList();
      final cur = widget.values[name] == null ? null : '${widget.values[name]}';
      input = DropdownButtonFormField<String>(
        initialValue: vals.contains(cur) ? cur : null,
        isExpanded: true,
        decoration: _deco(),
        items: [
          for (final o in opts)
            DropdownMenuItem(
                value: '${o['v']}',
                child: Text('${o['l']}',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13))),
        ],
        onChanged: (v) => setState(() => widget.values[name] = v),
      );
    } else if (kind == 'date' || kind == 'datetime') {
      final cur = '${widget.values[name] ?? ''}';
      input = InkWell(
        onTap: () async {
          final now = DateTime.now();
          final d = await showDatePicker(
              context: context,
              initialDate: now,
              firstDate: DateTime(now.year - 3),
              lastDate: DateTime(now.year + 3));
          if (d == null) return;
          final s = '${d.year.toString().padLeft(4, '0')}-'
              '${d.month.toString().padLeft(2, '0')}-'
              '${d.day.toString().padLeft(2, '0')}';
          setState(() => widget.values[name] =
              kind == 'datetime' ? '$s 09:00:00' : s);
        },
        child: InputDecorator(
          decoration: _deco(),
          child: Text(cur.isEmpty ? tr('اختر تاريخًا', 'Pick a date') : cur,
              style: TextStyle(
                  fontSize: 13,
                  color: cur.isEmpty ? Colors.grey.shade400 : Colors.black87)),
        ),
      );
    } else {
      input = TextField(
        keyboardType: (kind == 'int' || kind == 'float')
            ? const TextInputType.numberWithOptions(decimal: true)
            : (kind == 'text' ? TextInputType.multiline : TextInputType.text),
        maxLines: kind == 'text' ? 3 : 1,
        controller: TextEditingController(text: '${widget.values[name] ?? ''}')
          ..selection = TextSelection.collapsed(
              offset: '${widget.values[name] ?? ''}'.length),
        decoration: _deco(),
        onChanged: (v) => widget.values[name] = v,
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        input,
        if (f['help'] != null) ...[
          const SizedBox(height: 4),
          Text('${f['help']}',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
        ],
      ]),
    );
  }

  InputDecoration _deco() => InputDecoration(
        filled: true,
        fillColor: Colors.white,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: widget.accent, width: 1.5)),
      );
}
