import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// A professional "request a quote" form — sections the way an RFQ should read:
/// what you need, where and how long, which extras (admin-configurable), and
/// how to reach you. Submits a c2c.contract.request.
class C2CRfqSheet extends StatefulWidget {
  const C2CRfqSheet({super.key});
  @override
  State<C2CRfqSheet> createState() => _C2CRfqSheetState();
}

class _C2CRfqSheetState extends State<C2CRfqSheet> {
  final _title = TextEditingController();
  final _desc = TextEditingController();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _site = TextEditingController();
  final _sector = TextEditingController();

  int? _categoryId;
  String _audience = 'company';
  int _months = 12;
  String _budget = '';
  String _time = '';
  final Set<int> _options = {};

  List<dynamic> _cats = const [];
  List<dynamic> _rfqOptions = const [];
  bool _loading = true, _busy = false;

  // const cannot contain a method call, so the pair is stored and resolved
  // where it is rendered — same trick used for every other option list.
  static const _budgets = [('أقل من 500', 'Under 500'), ('500 – 2000', '500 – 2000'),
                           ('2000 – 5000', '2000 – 5000'), ('أكثر من 5000', 'Over 5000')];
  static const _times = [('صباحًا', 'Morning'), ('ظهرًا', 'Midday'),
                         ('مساءً', 'Evening'), ('أي وقت', 'Any time')];

  @override
  void initState() {
    super.initState();
    _load();
    final p = context.read<AuthProvider>().profile;
    if (p != null) _name.text = p.name;
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final results = await Future.wait([api.c2cCategoriesList(), api.c2cRfqOptions()]);
      if (mounted) setState(() { _cats = results[0]; _rfqOptions = results[1]; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    for (final c in [_title, _desc, _name, _phone, _site, _sector]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty || _name.text.trim().isEmpty || _phone.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('العنوان والاسم والهاتف مطلوبة', 'Title, name and phone are required')),
          backgroundColor: C2C.red));
      return;
    }
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.c2cContractCreate({
        'title': _title.text.trim(),
        'description': _desc.text.trim(),
        'customer_name': _name.text.trim(),
        'phone': _phone.text.trim(),
        'audience': _audience,
        'site_address': _site.text.trim(),
        'sector': _sector.text.trim(),
        'duration_months': _months,
        'budget_range': _budget,
        'preferred_time': _time,
        'category_id': _categoryId,
        'option_ids': _options.toList(),
      });
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.92, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (ctx, scroll) => Container(
        decoration: const BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        child: Column(children: [
          // header
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [C2C.redBright, C2C.red, C2C.redDeep],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
            ),
            child: SafeArea(bottom: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 8, 14),
              child: Row(children: [
                const Icon(Icons.request_quote_rounded, color: Colors.white, size: 22),
                const SizedBox(width: 9),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('طلب عرض سعر', 'Request a quote'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                  Text(tr('عبّئ التفاصيل ويصلك عرض مخصّص', 'Tell us your needs, get a tailored quote'),
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
                ])),
                IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white),
                    onPressed: () => Navigator.pop(context)),
              ]),
            )),
          ),
          if (_loading)
            const Expanded(child: Center(child: CircularProgressIndicator(color: C2C.red)))
          else
            Expanded(child: ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(14, 14, 14, 14), children: [
              _section('١', tr('ما الذي تحتاجه؟', 'What do you need?'), Icons.help_outline_rounded, [
                _field(_title, tr('عنوان الطلب *', 'Request title *'), Icons.title_rounded),
                if (_cats.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _label(tr('مجال الخدمة', 'Service area')),
                  Wrap(spacing: 7, runSpacing: 7, children: [
                    for (final c in _cats)
                      _chip('${c['icon'] ?? ''} ${c['name']}', _categoryId == c['id'],
                          () => setState(() => _categoryId = _categoryId == c['id'] ? null : c['id'] as int)),
                  ]),
                ],
                const SizedBox(height: 10),
                _field(_desc, tr('وصف الاحتياج', 'Describe your need'), Icons.notes_rounded, lines: 3),
              ]),
              _section('٢', tr('الجهة والمدة', 'Scope & duration'), Icons.business_rounded, [
                _label(tr('لمن الخدمة؟', 'For whom?')),
                Row(children: [
                  _chip(tr('منزل', 'Home'), _audience == 'home', () => setState(() => _audience = 'home')),
                  const SizedBox(width: 8),
                  _chip(tr('شركة/منشأة', 'Company'), _audience == 'company', () => setState(() => _audience = 'company')),
                ]),
                const SizedBox(height: 10),
                _field(_sector, tr('القطاع/النشاط (اختياري)', 'Sector (optional)'), Icons.category_rounded),
                const SizedBox(height: 10),
                _field(_site, tr('الموقع/العنوان', 'Site / address'), Icons.location_on_outlined),
                const SizedBox(height: 12),
                _label(tr('مدة التعاقد: $_months شهر', 'Contract: $_months months')),
                Slider(
                  value: _months.toDouble(), min: 1, max: 36, divisions: 35,
                  activeColor: C2C.red, label: '$_months',
                  onChanged: (v) => setState(() => _months = v.round()),
                ),
              ]),
              if (_rfqOptions.isNotEmpty)
                _section('٣', tr('خيارات إضافية', 'Extras'), Icons.tune_rounded, [
                  for (final o in _rfqOptions)
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      dense: true,
                      activeColor: C2C.red,
                      value: _options.contains(o['id']),
                      onChanged: (v) => setState(() {
                        if (v == true) {
                          _options.add(o['id'] as int);
                        } else {
                          _options.remove(o['id']);
                        }
                      }),
                      title: Text('${o['icon'] ?? '✅'} ${o['name']}',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                      subtitle: o['description'] != null
                          ? Text('${o['description']}', style: const TextStyle(fontSize: 11)) : null,
                    ),
                ]),
              _section('٤', tr('الميزانية والوقت', 'Budget & timing'), Icons.payments_rounded, [
                _label(tr('الميزانية التقديرية (KWD)', 'Estimated budget (KWD)')),
                Wrap(spacing: 7, runSpacing: 7, children: [
                  for (final b in _budgets)
                    _chip(tr(b.$1, b.$2), _budget == b.$1,
                        () => setState(() => _budget = _budget == b.$1 ? '' : b.$1)),
                ]),
                const SizedBox(height: 10),
                _label(tr('الوقت المفضّل للتواصل', 'Preferred contact time')),
                Wrap(spacing: 7, runSpacing: 7, children: [
                  for (final t in _times)
                    _chip(tr(t.$1, t.$2), _time == t.$1,
                        () => setState(() => _time = _time == t.$1 ? '' : t.$1)),
                ]),
              ]),
              _section('٥', tr('بيانات التواصل', 'Contact'), Icons.person_rounded, [
                _field(_name, tr('الاسم *', 'Name *'), Icons.badge_outlined),
                const SizedBox(height: 10),
                _field(_phone, tr('الهاتف *', 'Phone *'), Icons.phone_outlined, phone: true),
              ]),
              const SizedBox(height: 8),
            ])),
          if (!_loading)
            SafeArea(top: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
              child: SizedBox(height: 52, width: double.infinity, child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                onPressed: _busy ? null : _submit,
                icon: _busy
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.send_rounded),
                label: Text(tr('إرسال طلب عرض السعر', 'Send quote request'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              )),
            )),
        ]),
      ),
    );
  }

  Widget _section(String n, String title, IconData ic, List<Widget> children) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 26, height: 26, alignment: Alignment.center,
              decoration: BoxDecoration(color: C2C.red, borderRadius: BorderRadius.circular(9)),
              child: Text(n, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
            ),
            const SizedBox(width: 8),
            Icon(ic, size: 16, color: C2C.red),
            const SizedBox(width: 6),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: C2C.navy)),
          ]),
          const SizedBox(height: 12),
          ...children,
        ]),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: C2C.ink)),
      );

  Widget _field(TextEditingController c, String label, IconData ic, {int lines = 1, bool phone = false}) => TextField(
        controller: c, maxLines: lines,
        keyboardType: phone ? TextInputType.phone : null,
        decoration: InputDecoration(
          labelText: label, prefixIcon: Icon(ic, size: 19),
          filled: true, fillColor: C2C.bg, isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        ),
      );

  Widget _chip(String label, bool on, VoidCallback onTap) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: on ? C2C.red : Colors.white,
            borderRadius: BorderRadius.circular(11),
            border: Border.all(color: on ? C2C.red : Colors.grey.withValues(alpha: 0.3)),
          ),
          child: Text(label, style: TextStyle(
              color: on ? Colors.white : C2C.ink, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
      );
}

/// Opens the RFQ sheet; returns true if a request was submitted.
Future<bool?> openRfqSheet(BuildContext context) => showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => const C2CRfqSheet(),
    );
