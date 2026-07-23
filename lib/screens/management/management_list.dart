import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import '../pms/pms_employee_file.dart';
import '../pdf_report_screen.dart';
import '../excel_export.dart';

/// Parse a `#RRGGBB` string into a Color (falls back to slate).
Color mgmtHex(String? hex, [Color fallback = Mgmt.slate]) {
  if (hex == null || hex.isEmpty) return fallback;
  var h = hex.replaceAll('#', '').trim();
  if (h.length == 6) h = 'FF$h';
  final v = int.tryParse(h, radix: 16);
  return v == null ? fallback : Color(v);
}

/// A professional, state-coloured status chip used across list & detail.
/// Reads `state` (label) + `state_color` (#hex) from the record map.
Widget mgmtStateChip(Map src, {double fontSize = 10}) {
  final label = '${src['state'] ?? ''}';
  if (label.isEmpty) return const SizedBox.shrink();
  final c = mgmtHex('${src['state_color'] ?? ''}');
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
    decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.34))),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 6, height: 6, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
      const SizedBox(width: 5),
      Text(label, style: TextStyle(color: c, fontSize: fontSize, fontWeight: FontWeight.w800)),
    ]),
  );
}

/// Native list for one management system (purchases, tenders, employees, …).
/// The server returns only rows this user may read.
class ManagementListScreen extends StatefulWidget {
  const ManagementListScreen({
    super.key, required this.appKey, required this.title, required this.icon, required this.accent});
  final String appKey, title, icon;
  final Color accent;

  @override
  State<ManagementListScreen> createState() => _ManagementListScreenState();
}

class _ManagementListScreenState extends State<ManagementListScreen> {
  late Future<Map<String, dynamic>> _f;
  final _search = TextEditingController();
  Timer? _debounce;
  String _q = '';
  Map<String, dynamic>? _last;

  bool get _isProposals => widget.appKey == 'proposals';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() {
    final fut = context.read<AuthProvider>().api.managementList(widget.appKey, q: _q);
    fut.then((d) { if (mounted) setState(() => _last = d); }).catchError((_) {});
    setState(() => _f = fut);
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 420), () {
      if (!mounted) return;
      _q = v.trim();
      _reload();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      floatingActionButton: (_isProposals && _last?['can_create'] == true)
          ? FloatingActionButton.extended(
              backgroundColor: widget.accent,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.add_rounded),
              label: Text(tr('عرض سعر جديد', 'New quotation'),
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              onPressed: _createProposal)
          : null,
      appBar: AppBar(
        backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
        title: Row(children: [
          Text('${widget.icon} '),
          Expanded(child: Text(widget.title, overflow: TextOverflow.ellipsis)),
        ]),
      ),
      body: Column(children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: TextField(
            controller: _search,
            onChanged: _onSearch,
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              suffixIcon: _search.text.isEmpty ? null : IconButton(
                icon: const Icon(Icons.close_rounded, size: 18),
                onPressed: () { _search.clear(); _q = ''; _reload(); }),
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => _reload(),
            child: FutureBuilder<Map<String, dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (snap.hasError) {
                  return ListView(children: [Padding(
                    padding: const EdgeInsets.all(40),
                    child: Center(child: Text('${snap.error}',
                        textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))]);
                }
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final rows = (snap.data!['rows'] as List?) ?? [];
                final total = snap.data!['count'] ?? 0;
                if (rows.isEmpty) {
                  return ListView(children: [Padding(
                    padding: const EdgeInsets.only(top: 90),
                    child: Center(child: Text(tr('لا سجلات', 'No records'),
                        style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700))))]);
                }
                final stats = (snap.data!['stats'] as List?) ?? const [];
                final currency = '${snap.data!['currency'] ?? ''}';
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    if (i == 0) {
                      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        if (stats.isNotEmpty) _statsHeader(stats.cast<Map>()),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4, top: 2),
                          child: Text(
                              tr('عرض ${rows.length} من $total', 'Showing ${rows.length} of $total'),
                              style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w700)),
                        ),
                      ]);
                    }
                    final r = rows[i - 1] as Map;
                    if (_isProposals) return _proposalCard(r, currency);
                    if (widget.appKey == 'tenders') return _tenderCard(r, currency);
                    if (widget.appKey == 'employees') return _employeeCard(r);
                    if (widget.appKey == 'leaves') return _leaveCard(r);
                    if (widget.appKey == 'crm') return _crmCard(r, currency);
                    if (r['ord'] != null) return _orderCard(r, currency);
                    if (r['exp'] != null) return _expenseCard(r);
                    if (r['fl'] != null) return _fleetCard(r);
                    return _row(r);
                  },
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  Widget _row(Map r) => Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
            child: Row(children: [
              if ('${r['logo_b64'] ?? ''}'.isNotEmpty)
                _logoBox('${r['logo_b64']}', '${r['title']}', size: 40)
              else if (r['image'] != null)
                ClipRRect(borderRadius: BorderRadius.circular(10),
                    child: Image.network('${context.read<AuthProvider>().api.baseUrl.replaceAll('/api/v1', '')}${r['image']}',
                        width: 40, height: 40, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => _avatar(r)))
              else _avatar(r),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink, height: 1.25)),
                if (r['subtitle'] != null) Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['subtitle']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 11.5)),
                ),
                if (r['date'] != null) Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['date']}'.split(' ').first,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 10.5)),
                ),
              ])),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                if (r['amount'] != null)
                  Text('${r['amount']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
                if (r['state'] != null) Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: mgmtStateChip(r),
                ),
              ]),
            ]),
          ),
        ),
      );

  // ---- Proposals: KPI header + rich per-record cards --------------------
  Widget _statsHeader(List<Map> stats) {
    String fmt(Map s) {
      final v = s['value'];
      final unit = '${s['unit'] ?? ''}';
      final txt = (s['money'] == true && v is num)
          ? v.toStringAsFixed(3)
          : '$v';
      return unit.isEmpty ? txt : '$txt$unit';
    }
    return SizedBox(
      height: 78,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(vertical: 6),
        itemCount: stats.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final s = stats[i];
          final c = mgmtHex('${s['color'] ?? ''}', widget.accent);
          return Container(
            width: 122,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: c.withValues(alpha: 0.22))),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Row(children: [
                    Text('${s['icon'] ?? ''} ', style: const TextStyle(fontSize: 12)),
                    Expanded(
                      child: Text(gLang == 'en' ? '${s['en']}' : '${s['ar']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Mgmt.slate, fontSize: 10, fontWeight: FontWeight.w700)),
                    ),
                  ]),
                  const SizedBox(height: 5),
                  Text(fmt(s),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 16.5)),
                ]),
          );
        },
      ),
    );
  }

  Widget _miniStat(String icon, String label, String value, Color c) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$icon $label', style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 1),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 12.5)),
        ],
      );

  Widget _proposalCard(Map r, String currency) {
    final pr = (r['pr'] as Map?) ?? const {};
    final cur = currency.isEmpty ? '' : ' $currency';
    final margin = (pr['margin_pct'] as num?)?.toDouble() ?? 0;
    final marginColor = margin >= 20
        ? const Color(0xFF16A34A)
        : (margin >= 10 ? const Color(0xFFF59E0B) : Mgmt.red);
    final validityColor = mgmtHex('${pr['validity_color'] ?? ''}', Mgmt.slate);
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.fromLTRB(13, 12, 13, 11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // top row: ref + customer + state
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    if ('${pr['ref'] ?? ''}'.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        margin: const EdgeInsetsDirectional.only(end: 6),
                        decoration: BoxDecoration(
                            color: widget.accent.withValues(alpha: 0.10),
                            borderRadius: BorderRadius.circular(7)),
                        child: Text('${pr['ref']}',
                            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 10.5)),
                      ),
                    if (pr['service_type'] != null)
                      Expanded(
                        child: Text('${pr['service_type']}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Mgmt.ink, fontWeight: FontWeight.w800, fontSize: 12)),
                      ),
                  ]),
                  const SizedBox(height: 3),
                  Text('${pr['customer'] ?? r['subtitle'] ?? '—'}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                ]),
              ),
              mgmtStateChip(r),
            ]),
            const Divider(height: 16),
            // money row: cost · sale · profit%
            Row(children: [
              Expanded(child: _miniStat('💵', tr('التكلفة', 'Cost'),
                  '${(pr['cost'] as num?)?.toStringAsFixed(3) ?? '0'}$cur', Mgmt.ink)),
              Expanded(child: _miniStat('🏷️', tr('البيع', 'Sale'),
                  '${(pr['sale'] as num?)?.toStringAsFixed(3) ?? '0'}$cur', widget.accent)),
              Expanded(child: _miniStat('📈', tr('الربح', 'Profit'),
                  '${(pr['profit'] as num?)?.toStringAsFixed(3) ?? '0'}$cur  ·  ${margin.toStringAsFixed(1)}%', marginColor)),
            ]),
            const SizedBox(height: 9),
            // footer chips: manpower · services · validity · date
            Wrap(spacing: 6, runSpacing: 6, children: [
              if ((pr['manpower'] as num?) != null && (pr['manpower'] as num) > 0)
                _tag('👷 ${pr['manpower']}', Mgmt.slate),
              if ((pr['services'] as num?) != null && (pr['services'] as num) > 0)
                _tag('🧾 ${pr['services']}', Mgmt.slate),
              if ('${pr['validity_ar'] ?? ''}'.isNotEmpty && '${pr['validity']}' != 'none')
                _tag(gLang == 'en' ? '${pr['validity_en']}' : '${pr['validity_ar']}', validityColor),
              if (r['date'] != null)
                _tag('📅 ${'${r['date']}'.split(' ').first}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _tag(String text, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
        child: Text(text, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w700)),
      );

  Future<void> _createProposal() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _ProposalCreateSheet(accent: widget.accent),
    );
    if (created == null || !mounted) return;
    _reload();
    // open the fresh quotation straight away
    await _openDetail(created['id'] as int, '${created['title'] ?? ''}');
  }

  // ---- Tenders: logo + countdown + rich card ----------------------------
  Widget _logoBox(String? b64, String fallbackText, {double size = 46}) {
    Widget fb() => Container(
        width: size, height: size,
        decoration: BoxDecoration(
            color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(11)),
        alignment: Alignment.center,
        child: Text(fallbackText.trim().isEmpty ? '?' : fallbackText.trim().characters.first,
            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: size * 0.4)));
    if (b64 == null || b64.isEmpty) return fb();
    return ClipRRect(
      borderRadius: BorderRadius.circular(11),
      child: Image.memory(base64Decode(b64),
          width: size, height: size, fit: BoxFit.cover, gaplessPlayback: true,
          errorBuilder: (_, __, ___) => fb()),
    );
  }

  Widget _tenderCard(Map r, String currency) {
    final tn = (r['tn'] as Map?) ?? const {};
    final cur = '${tn['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    final dl = (tn['deadline'] as Map?) ?? const {};
    final dlColor = mgmtHex('${dl['color'] ?? ''}', Mgmt.slate);
    final prob = (tn['win_probability'] as num?)?.toDouble() ?? 0;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _logoBox('${tn['logo_b64'] ?? ''}', '${tn['organization'] ?? r['title']}'),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${tn['organization'] ?? r['title']}',
                      maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink, height: 1.25)),
                  if ('${tn['tender_no'] ?? ''}'.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text('#️⃣ ${tn['tender_no']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w600)),
                    ),
                ]),
              ),
              mgmtStateChip(r),
            ]),
            const Divider(height: 15),
            Row(children: [
              // deadline countdown
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
                  decoration: BoxDecoration(
                      color: dlColor.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: dlColor.withValues(alpha: 0.30))),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon((dl['urgent'] == true) ? Icons.timer_rounded : Icons.event_available_rounded, size: 14, color: dlColor),
                    const SizedBox(width: 5),
                    Flexible(child: Text(gLang == 'en' ? '${dl['en']}' : '${dl['ar']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: dlColor, fontSize: 11, fontWeight: FontWeight.w800))),
                  ]),
                ),
              ),
              const SizedBox(width: 8),
              if ((tn['price'] as num?) != null && (tn['price'] as num) > 0)
                Text('${(tn['price'] as num).toStringAsFixed(3)}$money',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              if (tn['closing_date'] != null)
                _tag('📅 ${'${tn['closing_date']}'.split(' ').first}', Mgmt.slate),
              if ((tn['guarantee'] as num?) != null && (tn['guarantee'] as num) > 0)
                _tag('🛡️ ${(tn['guarantee'] as num).toStringAsFixed(0)}$money', Mgmt.slate),
              if (prob > 0)
                _tag('📈 ${prob.toStringAsFixed(0)}%',
                    prob >= 60 ? const Color(0xFF16A34A) : (prob >= 35 ? const Color(0xFFF59E0B) : Mgmt.slate)),
              if ((tn['care_rank'] as num?) != null && (tn['care_rank'] as num) > 0)
                _tag('🥇 ${tr('ترتيبنا', 'Rank')} ${tn['care_rank']}', widget.accent),
              if (tn['winner'] != null)
                _tag('🏆 ${tn['winner']}', const Color(0xFF16A34A)),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Employees: photo + status + attendance ---------------------------
  Widget _employeeCard(Map r) {
    final e = (r['emp'] as Map?) ?? const {};
    final attColor = mgmtHex('${e['attendance_color'] ?? ''}', Mgmt.slate);
    final presColor = mgmtHex('${e['presence_color'] ?? ''}', Mgmt.slate);
    final onDuty = '${e['attendance']}' == 'checked_in';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            Stack(children: [
              _logoBox('${e['photo_b64'] ?? ''}', '${r['title']}', size: 48),
              if (onDuty)
                Positioned(
                  right: 0, bottom: 0,
                  child: Container(
                    width: 14, height: 14,
                    decoration: BoxDecoration(
                        color: const Color(0xFF16A34A), shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2)),
                  ),
                ),
            ]),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
                if (e['job'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('${e['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                  ),
                if (e['department'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('🏢 ${e['department']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 10)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  _tag(gLang == 'en' ? '${e['attendance_en']}' : '${e['attendance_ar']}', attColor),
                  _tag(gLang == 'en' ? '${e['presence_en']}' : '${e['presence_ar']}', presColor),
                  if (e['employee_type'] != null) _tag('${e['employee_type']}', Mgmt.slate),
                  if (e['active'] == false) _tag(tr('مؤرشف', 'Archived'), Mgmt.red),
                ]),
              ]),
            ),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      ),
    );
  }

  Widget _avatar(Map r) => Container(
        width: 40, height: 40,
        decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
        alignment: Alignment.center,
        child: Text('${r['title']}'.trim().isEmpty ? '?' : '${r['title']}'.trim().characters.first,
            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900)),
      );

  // ---- Orders (sales / purchases / invoices) ----------------------------
  Widget _orderCard(Map r, String currency) {
    final o = (r['ord'] as Map?) ?? const {};
    final cur = '${o['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _logoBox('${o['logo_b64'] ?? ''}', '${o['partner'] ?? r['title']}', size: 42),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${o['partner'] ?? r['title']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('${r['title']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w600)),
                  ),
                ]),
              ),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                if ((o['amount'] as num?) != null)
                  Text('${(o['amount'] as num).toStringAsFixed(3)}$money',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: widget.accent)),
                const SizedBox(height: 4),
                mgmtStateChip(r),
              ]),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              if (r['date'] != null) _tag('📅 ${'${r['date']}'.split(' ').first}', Mgmt.slate),
              if ((o['lines'] as num?) != null && (o['lines'] as num) > 0)
                _tag('🧾 ${o['lines']} ${tr('بند', 'items')}', Mgmt.slate),
              if (o['inv_ar'] != null)
                _tag(gLang == 'en' ? '${o['inv_en']}' : '${o['inv_ar']}', mgmtHex('${o['inv_color']}', Mgmt.slate)),
              if (o['pay_label'] != null)
                _tag('💳 ${o['pay_label']}', mgmtHex('${o['pay_color']}', Mgmt.slate)),
              if (o['salesperson'] != null) _tag('👤 ${o['salesperson']}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Leaves (time off) ------------------------------------------------
  Widget _leaveCard(Map r) {
    final l = (r['lv'] as Map?) ?? const {};
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${l['photo_b64'] ?? ''}', '${l['employee'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text('${l['employee'] ?? r['title']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
                  ),
                  mgmtStateChip(r),
                ]),
                if (l['leave_type'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('🌴 ${l['leave_type']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if ((l['days'] as num?) != null)
                    _tag('⏱️ ${l['days']} ${tr('يوم', 'days')}', widget.accent),
                  if (l['date_from'] != null)
                    _tag('${'${l['date_from']}'.split(' ').first} → ${'${l['date_to'] ?? ''}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- CRM (opportunities) ----------------------------------------------
  Widget _crmCard(Map r, String currency) {
    final o = (r['crm'] as Map?) ?? const {};
    final cur = '${o['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    final prob = (o['probability'] as num?)?.toDouble() ?? 0;
    final stageColor = mgmtHex('${o['stage_color'] ?? ''}', widget.accent);
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${o['logo_b64'] ?? ''}', '${o['partner'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                if (o['partner'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('🏢 ${o['partner']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (o['stage'] != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                          color: stageColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: stageColor.withValues(alpha: 0.34))),
                      child: Text('${o['stage']}', style: TextStyle(color: stageColor, fontSize: 10, fontWeight: FontWeight.w800)),
                    ),
                  if (prob > 0) _tag('📈 ${prob.toStringAsFixed(0)}%',
                      prob >= 70 ? const Color(0xFF16A34A) : (prob >= 40 ? const Color(0xFFF59E0B) : Mgmt.slate)),
                  if (o['salesperson'] != null) _tag('👤 ${o['salesperson']}', Mgmt.slate),
                ]),
              ]),
            ),
            if ((o['expected'] as num?) != null && (o['expected'] as num) > 0)
              Text('${(o['expected'] as num).toStringAsFixed(0)}$money',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
          ]),
        ),
      ),
    );
  }

  // ---- Employee expenses ------------------------------------------------
  Widget _expenseCard(Map r) {
    final e = (r['exp'] as Map?) ?? const {};
    final cur = '${e['currency'] ?? ''}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${e['photo_b64'] ?? ''}', '${e['employee'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                if (e['employee'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('👤 ${e['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if ((e['lines'] as num?) != null && (e['lines'] as num) > 0)
                    _tag('🧾 ${e['lines']} ${tr('بند', 'items')}', Mgmt.slate),
                  if (e['payment_mode'] != null) _tag('💳 ${e['payment_mode']}', Mgmt.slate),
                ]),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              if ((e['amount'] as num?) != null)
                Text('${(e['amount'] as num).toStringAsFixed(3)}$money',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
              const SizedBox(height: 4),
              mgmtStateChip(r),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Fleet (vehicles) -------------------------------------------------
  Widget _fleetCard(Map r) {
    final v = (r['fl'] as Map?) ?? const {};
    final stColor = mgmtHex('${v['state_color'] ?? ''}', const Color(0xFF16A34A));
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            SizedBox(
              width: 56, height: 56,
              child: '${v['image_b64'] ?? ''}'.isEmpty
                  ? Container(
                      decoration: BoxDecoration(
                          color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(11)),
                      child: Icon(Icons.directions_car_rounded, color: widget.accent, size: 26))
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(11),
                      child: Image.memory(base64Decode('${v['image_b64']}'),
                          width: 56, height: 56, fit: BoxFit.cover, gaplessPlayback: true,
                          errorBuilder: (_, __, ___) => Icon(Icons.directions_car_rounded, color: widget.accent, size: 26))),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text('${v['model'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                  ),
                  if (r['state'] != null) mgmtStateChip(r),
                ]),
                if ('${v['plate'] ?? ''}'.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                          color: Mgmt.ink, borderRadius: BorderRadius.circular(5)),
                      child: Text('🔖 ${v['plate']}',
                          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900, letterSpacing: 1)),
                    ),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (v['driver'] != null) _tag('🧑‍✈️ ${v['driver']}', const Color(0xFF16A34A))
                  else _tag(tr('بدون سائق', 'No driver'), Mgmt.slate),
                  if ((v['odometer'] as num?) != null && (v['odometer'] as num) > 0)
                    _tag('🛣️ ${(v['odometer'] as num).toStringAsFixed(0)} ${tr('كم', 'km')}', Mgmt.slate),
                  if (v['fuel'] != null) _tag('⛽ ${v['fuel']}', Mgmt.slate),
                  if (v['year'] != null) _tag('📆 ${v['year']}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _openDetail(int id, String title) async {
    // Employees open the full PMS-style file: photo, tags, and the tappable
    // icon-tile hub (documents, payslips, leaves, allowances, EOS, skills…).
    if (widget.appKey == 'employees') {
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PmsEmployeeFileScreen(employeeId: id, name: title)));
      return;
    }
    Map<String, dynamic>? d;
    try {
      d = await context.read<AuthProvider>().api.managementDetail(widget.appKey, id);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
      return;
    }
    if (!mounted || d == null) return;
    if (!mounted) return;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _DetailSheet(
          appKey: widget.appKey, accent: widget.accent, initial: d!, onChanged: _reload),
    );
  }
}

/// Open one management record from anywhere (e.g. global search): employees →
/// the rich PMS file, everything else → the detail sheet with its actions.
Future<void> openManagementRecord(BuildContext context, String key, int id,
    {String title = '', Color accent = Mgmt.red}) async {
  if (key == 'employees') {
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PmsEmployeeFileScreen(employeeId: id, name: title)));
    return;
  }
  Map<String, dynamic>? d;
  try {
    d = await context.read<AuthProvider>().api.managementDetail(key, id);
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    }
    return;
  }
  if (!context.mounted || d == null) return;
  await showModalBottomSheet(
    context: context, isScrollControlled: true, backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => _DetailSheet(appKey: key, accent: accent, initial: d!, onChanged: () {}),
  );
}

/// Record detail + its whitelisted workflow actions.
class _DetailSheet extends StatefulWidget {
  const _DetailSheet({required this.appKey, required this.accent, required this.initial, required this.onChanged});
  final String appKey;
  final Color accent;
  final Map<String, dynamic> initial;
  final VoidCallback onChanged;
  @override
  State<_DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<_DetailSheet> {
  late Map<String, dynamic> d = widget.initial;
  bool _busy = false;

  Future<void> _run(Map a) async {
    if (a['confirm'] == true) {
      final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(tr('تأكيد الإجراء', 'Confirm action'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: Text(tr('هل تريد تنفيذ «${a['ar']}»؟', 'Run "${a['en']}"?')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Mgmt.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('نعم', 'Yes'))),
        ],
      ));
      if (ok != true) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api
          .managementAction(widget.appKey, d['id'] as int, '${a['key']}');
      if (!mounted) return;
      setState(() { d['state'] = res['state']; d['actions'] = res['actions']; });
      widget.onChanged();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم: ${a['ar']}', '✅ Done: ${a['en']}')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reload() async {
    try {
      final fresh = await context
          .read<AuthProvider>()
          .api
          .managementDetail(widget.appKey, d['id'] as int);
      if (mounted) setState(() => d = fresh);
    } catch (_) {}
  }

  Future<void> _editSheet() async {
    final editable = ((d['editable'] as List?) ?? const []).cast<Map>();
    if (editable.isEmpty) return;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _EditSheet(
          appKey: widget.appKey,
          id: d['id'] as int,
          accent: widget.accent,
          title: '${d['title']}',
          editable: editable),
    );
    if (saved == true) {
      await _reload();
      widget.onChanged();
    }
  }

  // ---- value rendering by type ------------------------------------------
  Widget _fieldRow(Map f) {
    final t = '${f['type']}';
    final v = '${f['value']}';
    Widget value;
    if (t == 'monetary' || t == 'float') {
      value = Text(v,
          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: widget.accent));
    } else if (t == 'many2one') {
      value = Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(
            color: widget.accent.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(8)),
        child: Text(v,
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: widget.accent)),
      );
    } else {
      value = Text(v,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink));
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
            width: 120,
            child: Text('${f['label']}',
                style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
        const SizedBox(width: 6),
        Expanded(child: Align(alignment: AlignmentDirectional.centerStart, child: value)),
      ]),
    );
  }

  String _reportPath(Map r) =>
      '/api/v1/management/${widget.appKey}/${d['id']}/report?report=${Uri.encodeQueryComponent('${r['report']}')}';

  Future<void> _openReport(Map r) async {
    final path = _reportPath(r);
    if ('${r['type']}' == 'xlsx') {
      await exportExcelFile(context, path: path,
          fileName: '${widget.appKey}-${d['id']}.xlsx');
    } else {
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
          path: path, title: gLang == 'en' ? '${r['en']}' : '${r['ar']}',
          fileName: '${widget.appKey}-${d['id']}.pdf')));
    }
  }

  Widget _reportsCard() {
    final reports = (d['reports'] as List?) ?? const [];
    if (reports.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.description_rounded, size: 16, color: widget.accent),
          const SizedBox(width: 6),
          Text(tr('التقارير', 'Reports'), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final r in reports.cast<Map>())
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                  foregroundColor: '${r['type']}' == 'xlsx' ? const Color(0xFF16A34A) : widget.accent,
                  side: BorderSide(color: ('${r['type']}' == 'xlsx' ? const Color(0xFF16A34A) : widget.accent).withValues(alpha: 0.5)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
              onPressed: _busy ? null : () => _openReport(r),
              icon: Icon('${r['type']}' == 'xlsx' ? Icons.table_chart_rounded : Icons.picture_as_pdf_rounded, size: 16),
              label: Text(gLang == 'en' ? '${r['en']}' : '${r['ar']}',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5)),
            ),
        ]),
      ]),
    );
  }

  Widget _linesCard() {
    final lines = (d['lines'] as List?) ?? const [];
    if (lines.isEmpty) return const SizedBox.shrink();
    final cur = d['currency'] ?? '';
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Row(children: [
            Text('🧾 ', style: const TextStyle(fontSize: 14)),
            Text(tr('البنود (${lines.length})', 'Line items (${lines.length})'),
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
          ]),
        ),
        for (final l in lines.cast<Map>())
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${l['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Mgmt.ink)),
                if (l['qty'] != null || l['price'] != null)
                  Text([
                    if (l['qty'] != null) '${tr('كمية', 'Qty')}: ${l['qty']}',
                    if (l['price'] != null) '${tr('سعر', 'Unit')}: ${l['price']}',
                  ].join('  ·  '), style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
              ])),
              if (l['subtotal'] != null)
                Text('${l['subtotal']} $cur',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
            ]),
          ),
      ]),
    );
  }

  Widget _sectionCard(Map s) {
    final fields = (s['fields'] as List?) ?? const [];
    if (fields.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
          decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Row(children: [
            Text('${s['icon'] ?? '📋'} ', style: const TextStyle(fontSize: 14)),
            Text(gLang == 'en' ? '${s['title_en'] ?? s['title']}' : '${s['title']}',
                style: TextStyle(
                    fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
          child: Column(children: [for (final f in fields) _fieldRow(f as Map)]),
        ),
      ]),
    );
  }

  // ---- Proposals: professional detail blocks ----------------------------
  Future<void> _sendProposal() async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('إرسال إلى العميل', 'Send to client'),
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Text(tr(
          'سيتم إرسال هذا العرض بالبريد إلى ${(d['proposal'] as Map?)?['send_email'] ?? 'العميل'}.',
          'This quotation will be emailed to ${(d['proposal'] as Map?)?['send_email'] ?? 'the client'}.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(backgroundColor: widget.accent, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(c, true),
          icon: const Icon(Icons.send_rounded, size: 16),
          label: Text(tr('إرسال', 'Send'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.managementProposalSend(d['id'] as int);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ أُرسل العرض إلى ${res['email']}', '✅ Sent to ${res['email']}')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _kpiCell(String label, String value, Color c, {bool big = false}) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: big ? 18 : 14.5)),
        ],
      );

  Widget _proposalBlock() {
    final p = d['proposal'] as Map?;
    if (p == null) return const SizedBox.shrink();
    final h = (p['header'] as Map?) ?? const {};
    final dates = (p['dates'] as Map?) ?? const {};
    final breakdown = (p['breakdown'] as List?) ?? const [];
    final info = (p['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final margin = (h['margin_pct'] as num?)?.toDouble() ?? 0;
    final marginColor = margin >= 20
        ? const Color(0xFF16A34A)
        : (margin >= 10 ? const Color(0xFFF59E0B) : Mgmt.red);
    final validityColor = mgmtHex('${dates['validity_color'] ?? ''}', Mgmt.slate);

    return Column(children: [
      // ---- money KPI card: cost / sale / profit / margin
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('سعر البيع', 'Sale price'), m(h['sale']), widget.accent, big: true)),
            Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: _kpiCell(tr('التكلفة', 'Cost'), m(h['cost']), Mgmt.ink, big: true)),
          ]),
          const Divider(height: 20),
          Row(children: [
            Expanded(child: _kpiCell(tr('صافي الربح', 'Net profit'), m(h['profit']), marginColor)),
            Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(
              child: Row(children: [
                Expanded(child: _kpiCell(tr('نسبة الربح', 'Margin %'), '${margin.toStringAsFixed(1)}%', marginColor)),
                _pctRing(margin, marginColor),
              ]),
            ),
          ]),
          if ((h['individual_sales'] as num?) != null && (h['individual_sales'] as num) > 0) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Text('👤 ${tr('للفرد', 'Per person')}',
                    style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700)),
                const Spacer(),
                Text('${tr('تكلفة', 'cost')} ${m(h['individual_cost'])}  ·  ${tr('بيع', 'sale')} ${m(h['individual_sales'])}',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 11, fontWeight: FontWeight.w800)),
              ]),
            ),
          ],
        ]),
      ),
      // ---- dates & validity strip
      if (dates.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Wrap(spacing: 14, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
            if (dates['proposal_date'] != null)
              _dateChip('📅', tr('تاريخ العرض', 'Date'), '${dates['proposal_date']}'.split(' ').first),
            if (dates['expire_date'] != null)
              _dateChip('⏰', tr('ينتهي', 'Expires'), '${dates['expire_date']}'.split(' ').first),
            if (dates['mobilization_date'] != null)
              _dateChip('🚩', tr('المباشرة', 'Mobilize'), '${dates['mobilization_date']}'.split(' ').first),
            if ((dates['period'] as num?) != null && (dates['period'] as num) > 0)
              _dateChip('🗓️', tr('المدة', 'Period'), '${dates['period']} ${tr('شهر', 'mo')}'),
            if ('${dates['validity']}' != 'none')
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                    color: validityColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: validityColor.withValues(alpha: 0.34))),
                child: Text(
                    '${gLang == 'en' ? dates['validity_en'] : dates['validity_ar']}'
                    '${(dates['days_to_expire'] as num?) != null && (dates['days_to_expire'] as num) > 0 ? ' · ${dates['days_to_expire']}${tr('ي', 'd')}' : ''}',
                    style: TextStyle(color: validityColor, fontSize: 10.5, fontWeight: FontWeight.w800)),
              ),
          ]),
        ),
      // ---- send-to-client
      if (p['can_send'] == true)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: SizedBox(
            width: double.infinity, height: 46,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : _sendProposal,
              icon: const Icon(Icons.send_rounded, size: 18),
              label: Text(tr('إرسال إلى العميل', 'Send to client'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
            ),
          ),
        ),
      // ---- cost breakdown
      if (breakdown.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
              child: Row(children: [
                const Text('🧮 ', style: TextStyle(fontSize: 14)),
                Text(tr('مكوّنات التكلفة', 'Cost breakdown'),
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
              ]),
            ),
            for (final b in breakdown.cast<Map>())
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                child: Row(children: [
                  Expanded(child: Text(gLang == 'en' ? '${b['en']}' : '${b['ar']}',
                      style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w600))),
                  Text(m(b['value']),
                      style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w800)),
                ]),
              ),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 9, 14, 11),
              decoration: BoxDecoration(
                  color: widget.accent.withValues(alpha: 0.05),
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16))),
              child: Row(children: [
                Expanded(child: Text(tr('إجمالي التكلفة', 'Total cost'),
                    style: TextStyle(color: widget.accent, fontSize: 12.5, fontWeight: FontWeight.w900))),
                Text(m(h['cost']),
                    style: TextStyle(color: widget.accent, fontSize: 13.5, fontWeight: FontWeight.w900)),
              ]),
            ),
          ]),
        ),
      // ---- service info
      if (info.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
              child: Row(children: [
                const Text('🧾 ', style: TextStyle(fontSize: 14)),
                Text(tr('بيانات الخدمة والتفاصيل', 'Service details'),
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(6, 4, 6, 8),
              child: Column(children: [
                for (final f in info.cast<Map>())
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${f['icon'] ?? '•'}  ', style: const TextStyle(fontSize: 13)),
                      SizedBox(width: 96, child: Text(gLang == 'en' ? '${f['en']}' : '${f['ar']}',
                          style: const TextStyle(color: Mgmt.slate, fontSize: 11.5))),
                      const SizedBox(width: 6),
                      Expanded(child: Text('${f['value']}',
                          style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
                    ]),
                  ),
              ]),
            ),
          ]),
        ),
    ]);
  }

  Widget _dateChip(String icon, String label, String value) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$icon $label', style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 1),
          Text(value, style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w800)),
        ],
      );

  Widget _pctRing(double pct, Color c) => SizedBox(
        width: 34, height: 34,
        child: Stack(alignment: Alignment.center, children: [
          SizedBox(
            width: 34, height: 34,
            child: CircularProgressIndicator(
                value: (pct.clamp(0, 100)) / 100.0, strokeWidth: 4,
                backgroundColor: c.withValues(alpha: 0.15),
                valueColor: AlwaysStoppedAnimation(c)),
          ),
          Text('${pct.round()}', style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w900)),
        ]),
      );

  Widget _sectionHead(String icon, String title) => Container(
        padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
        decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
        child: Row(children: [
          Text('$icon ', style: const TextStyle(fontSize: 14)),
          Text(title, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
        ]),
      );

  Widget _cardWrap(List<Widget> children) => Container(
        margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );

  Widget _infoRows(List info) => Padding(
        padding: const EdgeInsets.fromLTRB(6, 4, 6, 8),
        child: Column(children: [
          for (final f in info.cast<Map>())
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${f['icon'] ?? '•'}  ', style: const TextStyle(fontSize: 13)),
                SizedBox(width: 108, child: Text(gLang == 'en' ? '${f['en']}' : '${f['ar']}',
                    style: const TextStyle(color: Mgmt.slate, fontSize: 11.5))),
                const SizedBox(width: 6),
                Expanded(child: Text('${f['value']}',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
              ]),
            ),
        ]),
      );

  Future<void> _openTenderTab(String code, String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementTenderTab(d['id'] as int, code);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    final lines = (res['lines'] as List?) ?? const [];
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
        builder: (_, sc) => Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 14, 12, 12),
            decoration: BoxDecoration(
                gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
            child: Row(children: [
              Expanded(child: Text('$label · ${lines.length}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ),
          Expanded(
            child: lines.isEmpty
                ? Center(child: Text(tr('لا بيانات', 'No data'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700)))
                : ListView.separated(
                    controller: sc, padding: const EdgeInsets.all(12),
                    itemCount: lines.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final l = lines[i] as Map;
                      final pairs = (l['pairs'] as List?) ?? const [];
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                            color: Mgmt.bg, borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${l['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                          if (pairs.isNotEmpty) const SizedBox(height: 6),
                          for (final p in pairs.cast<Map>())
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 3),
                              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                SizedBox(width: 120, child: Text('${p['label']}',
                                    style: const TextStyle(color: Mgmt.slate, fontSize: 11))),
                                const SizedBox(width: 6),
                                Expanded(child: Text('${p['value']}',
                                    style: TextStyle(
                                        color: (p['type'] == 'float' || p['type'] == 'monetary') ? widget.accent : Mgmt.ink,
                                        fontSize: 12, fontWeight: FontWeight.w700))),
                              ]),
                            ),
                        ]),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _tenderBlock() {
    final t = d['tender'] as Map?;
    if (t == null) return const SizedBox.shrink();
    final h = (t['header'] as Map?) ?? const {};
    final dates = (t['dates'] as Map?) ?? const {};
    final info = (t['service_info'] as List?) ?? const [];
    final tabs = (t['tabs'] as List?) ?? const [];
    final prep = (t['prep'] as Map?) ?? const {};
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final dl = (dates['deadline'] as Map?) ?? const {};
    final dlColor = mgmtHex('${dl['color'] ?? ''}', Mgmt.slate);
    final prob = (h['win_probability'] as num?)?.toDouble() ?? 0;
    final probColor = prob >= 60 ? const Color(0xFF16A34A) : (prob >= 35 ? const Color(0xFFF59E0B) : Mgmt.slate);
    final prep1 = (prep['checklist_total'] as num?) ?? 0;
    final prep2 = (prep['requirement_total'] as num?) ?? 0;

    return Column(children: [
      // financial KPI card
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('قيمة المناقصة', 'Tender value'), m(h['price']), widget.accent, big: true)),
            if ((h['our_price'] as num?) != null && (h['our_price'] as num) > 0) ...[
              Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
              const SizedBox(width: 10),
              Expanded(child: _kpiCell(tr('سعرنا', 'Our price'), m(h['our_price']), Mgmt.ink, big: true)),
            ],
          ]),
          const Divider(height: 20),
          Row(children: [
            Expanded(child: _kpiCell(tr('احتمالية الفوز', 'Win prob.'), '${prob.toStringAsFixed(0)}%', probColor)),
            _pctRing(prob, probColor),
            const SizedBox(width: 10),
            Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: _kpiCell(tr('الضمان', 'Guarantee'), m(h['guarantee']), Mgmt.ink)),
          ]),
          if ((h['price_gap'] as num?) != null && (h['price_gap'] as num) != 0) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Text('📊 ${tr('فارق السعر', 'Price gap')}', style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700)),
                const Spacer(),
                Text('${m(h['price_gap'])}  ·  ${(h['price_gap_pct'] as num?)?.toStringAsFixed(1) ?? '0'}%',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 11.5, fontWeight: FontWeight.w800)),
              ]),
            ),
          ],
        ]),
      ),
      // dates & deadline strip
      Container(
        margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Wrap(spacing: 14, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
          if (dates['issue_date'] != null) _dateChip('📢', tr('الطرح', 'Issued'), '${dates['issue_date']}'.split(' ').first),
          if (dates['closing_date'] != null) _dateChip('⏰', tr('الإغلاق', 'Closing'), '${dates['closing_date']}'.split(' ').first),
          if (dates['meeting_date'] != null) _dateChip('🤝', tr('الاجتماع', 'Meeting'), '${dates['meeting_date']}'.split(' ').first),
          if ((dates['period'] as num?) != null && (dates['period'] as num) > 0)
            _dateChip('🗓️', tr('المدة', 'Period'), '${dates['period']} ${tr('شهر', 'mo')}'),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
                color: dlColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                border: Border.all(color: dlColor.withValues(alpha: 0.34))),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon((dl['urgent'] == true) ? Icons.timer_rounded : Icons.event_available_rounded, size: 13, color: dlColor),
              const SizedBox(width: 5),
              Text(gLang == 'en' ? '${dl['en']}' : '${dl['ar']}',
                  style: TextStyle(color: dlColor, fontSize: 10.5, fontWeight: FontWeight.w800)),
            ]),
          ),
        ]),
      ),
      // preparation progress
      if (prep1 > 0 || prep2 > 0)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Row(children: [
            if (prep1 > 0)
              Expanded(child: _progressLine('✅ ${tr('التحضير', 'Checklist')}',
                  (prep['checklist_pct'] as num?)?.toDouble() ?? 0, '${prep['checklist_done']}/${prep['checklist_total']}')),
            if (prep1 > 0 && prep2 > 0) const SizedBox(width: 16),
            if (prep2 > 0)
              Expanded(child: _progressLine('📋 ${tr('المتطلبات', 'Requirements')}',
                  (prep['requirement_pct'] as num?)?.toDouble() ?? 0, '${prep['requirement_ready']}/${prep['requirement_total']}')),
          ]),
        ),
      // tab tiles (backend tabs: price analysis, manpower, …)
      if (tabs.isNotEmpty)
        _cardWrap([
          _sectionHead('🗂️', tr('التبويبات والتحليلات', 'Tabs & analysis')),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 12),
            child: Wrap(spacing: 9, runSpacing: 9, children: [
              for (final tab in tabs.cast<Map>()) _tabTile(tab),
            ]),
          ),
        ]),
      // organization & tender info
      if (info.isNotEmpty)
        _cardWrap([
          _sectionHead('🏢', tr('بيانات الجهة والمناقصة', 'Organization & tender')),
          _infoRows(info),
        ]),
    ]);
  }

  Widget _progressLine(String label, double pct, String frac) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(child: Text(label, style: const TextStyle(color: Mgmt.ink, fontSize: 11.5, fontWeight: FontWeight.w800))),
            Text(frac, style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
                value: (pct.clamp(0, 100)) / 100.0, minHeight: 7,
                backgroundColor: widget.accent.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation(widget.accent)),
          ),
        ],
      );

  Widget _tabTile(Map tab) {
    final count = (tab['count'] as num?)?.toInt() ?? 0;
    final enabled = count > 0;
    final label = gLang == 'en' ? '${tab['en']}' : '${tab['ar']}';
    return SizedBox(
      width: (MediaQuery.of(context).size.width - 28 - 20 - 18) / 3,
      child: Opacity(
        opacity: enabled ? 1 : 0.5,
        child: Material(
          color: widget.accent.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(13),
          child: InkWell(
            borderRadius: BorderRadius.circular(13),
            onTap: enabled && !_busy ? () => _openTenderTab('${tab['code']}', label) : null,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(13),
                  border: Border.all(color: widget.accent.withValues(alpha: 0.16))),
              child: Column(children: [
                Stack(clipBehavior: Clip.none, children: [
                  Text('${tab['icon']}', style: const TextStyle(fontSize: 22)),
                  if (count > 0)
                    Positioned(
                      right: -10, top: -6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(color: widget.accent, borderRadius: BorderRadius.circular(10)),
                        child: Text('$count', style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900)),
                      ),
                    ),
                ]),
                const SizedBox(height: 7),
                Text(label, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Mgmt.ink, height: 1.15)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _orderBlock() {
    final o = d['order'] as Map?;
    if (o == null) return const SizedBox.shrink();
    final h = (o['header'] as Map?) ?? const {};
    final st = (o['status'] as Map?) ?? const {};
    final info = (o['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final hasPaid = h['residual'] != null;
    final residual = (h['residual'] as num?)?.toDouble() ?? 0;
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('الإجمالي', 'Total'), m(h['total']), widget.accent, big: true)),
            Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              _miniKV(tr('قبل الضريبة', 'Untaxed'), m(h['untaxed'])),
              const SizedBox(height: 4),
              _miniKV(tr('الضريبة', 'Tax'), m(h['tax'])),
            ])),
          ]),
          if (hasPaid) ...[
            const Divider(height: 20),
            Row(children: [
              Expanded(child: _kpiCell(tr('المدفوع', 'Paid'), m(h['paid']), const Color(0xFF16A34A))),
              Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
              const SizedBox(width: 10),
              Expanded(child: _kpiCell(tr('المتبقّي', 'Residual'), m(h['residual']),
                  residual > 0 ? Mgmt.red : const Color(0xFF16A34A))),
            ]),
          ],
          if (st.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              if (st['inv_ar'] != null)
                _statusPill('🧾', gLang == 'en' ? '${st['inv_en']}' : '${st['inv_ar']}', mgmtHex('${st['inv_color']}', Mgmt.slate)),
              if (st['pay_label'] != null)
                _statusPill('💳', '${st['pay_label']}', mgmtHex('${st['pay_color']}', Mgmt.slate)),
            ]),
          ],
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([
          _sectionHead('🏢', tr('بيانات الطرف والتفاصيل', 'Partner & details')),
          _infoRows(info),
        ]),
    ]);
  }

  Widget _miniKV(String k, String v) => Row(children: [
        Expanded(child: Text(k, style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w600))),
        Text(v, style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w800)),
      ]);

  Widget _statusPill(String icon, String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
            border: Border.all(color: c.withValues(alpha: 0.34))),
        child: Text('$icon $label', style: TextStyle(color: c, fontSize: 11.5, fontWeight: FontWeight.w800)),
      );

  Widget _fleetBlock() {
    final v = d['fleet'] as Map?;
    if (v == null) return const SizedBox.shrink();
    final specs = (v['service_info'] as List?) ?? (v['specs'] as List?) ?? const [];
    final counts = (v['counts'] as List?) ?? const [];
    final img = '${v['image_b64'] ?? ''}';
    return Column(children: [
      // photo banner + plate
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), color: widget.accent.withValues(alpha: 0.06)),
        child: Column(children: [
          SizedBox(
            height: 150, width: double.infinity,
            child: img.isEmpty
                ? Icon(Icons.directions_car_rounded, size: 60, color: widget.accent.withValues(alpha: 0.5))
                : Image.memory(base64Decode(img), fit: BoxFit.cover, gaplessPlayback: true,
                    errorBuilder: (_, __, ___) => Icon(Icons.directions_car_rounded, size: 60, color: widget.accent.withValues(alpha: 0.5))),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              if ('${v['plate'] ?? ''}'.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(color: Mgmt.ink, borderRadius: BorderRadius.circular(7)),
                  child: Text('🔖 ${v['plate']}',
                      style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: 2)),
                ),
              const Spacer(),
              if (v['model'] != null)
                Flexible(child: Text('${v['model']}', textAlign: TextAlign.end, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
            ]),
          ),
        ]),
      ),
      // count tiles
      if (counts.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final ct in counts.cast<Map>()) ...[
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                      color: Colors.white, borderRadius: BorderRadius.circular(13),
                      border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
                  child: Column(children: [
                    Text('${ct['icon']}', style: const TextStyle(fontSize: 18)),
                    const SizedBox(height: 3),
                    Text('${ct['count']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: widget.accent)),
                    Text(gLang == 'en' ? '${ct['en']}' : '${ct['ar']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
                  ]),
                ),
              ),
            ],
          ]),
        ),
      if (specs.isNotEmpty)
        _cardWrap([_sectionHead('🚗', tr('مواصفات المركبة', 'Vehicle specs')), _infoRows(specs)]),
    ]);
  }

  Widget _crmBlock() {
    final c = d['crm'] as Map?;
    if (c == null) return const SizedBox.shrink();
    final h = (c['header'] as Map?) ?? const {};
    final info = (c['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    final prob = (h['probability'] as num?)?.toDouble() ?? 0;
    final stageColor = mgmtHex('${h['stage_color'] ?? ''}', widget.accent);
    final probColor = prob >= 70 ? const Color(0xFF16A34A) : (prob >= 40 ? const Color(0xFFF59E0B) : Mgmt.slate);
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          Expanded(child: _kpiCell(tr('الإيراد المتوقع', 'Expected revenue'),
              '${(h['expected'] as num?)?.toStringAsFixed(3) ?? '0'}${cur.isEmpty ? '' : ' $cur'}', widget.accent, big: true)),
          Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
          const SizedBox(width: 12),
          Column(mainAxisSize: MainAxisSize.min, children: [
            _pctRing(prob, probColor),
            const SizedBox(height: 4),
            Text('${prob.toStringAsFixed(0)}%', style: TextStyle(color: probColor, fontWeight: FontWeight.w900, fontSize: 12)),
          ]),
        ]),
      ),
      if (h['stage'] != null)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Align(
            alignment: AlignmentDirectional.centerStart,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                  color: stageColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: stageColor.withValues(alpha: 0.34))),
              child: Text('🎯 ${h['stage']}', style: TextStyle(color: stageColor, fontSize: 12, fontWeight: FontWeight.w800)),
            ),
          ),
        ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📇', tr('بيانات الفرصة والتواصل', 'Opportunity & contact')), _infoRows(info)]),
    ]);
  }

  Widget _leaveBlock() {
    final lv = d['leave'] as Map?;
    if (lv == null) return const SizedBox.shrink();
    final info = (lv['service_info'] as List?) ?? const [];
    final photo = '${lv['photo_b64'] ?? ''}';
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          if (photo.isNotEmpty)
            ClipRRect(borderRadius: BorderRadius.circular(30),
                child: Image.memory(base64Decode(photo), width: 54, height: 54, fit: BoxFit.cover, gaplessPlayback: true)),
          if (photo.isNotEmpty) const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${lv['employee'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Mgmt.ink)),
            if (lv['leave_type'] != null)
              Padding(padding: const EdgeInsets.only(top: 2),
                  child: Text('🌴 ${lv['leave_type']}', style: const TextStyle(color: Mgmt.slate, fontSize: 12, fontWeight: FontWeight.w600))),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${lv['days'] ?? 0}', style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 22)),
            Text(tr('يوم', 'days'), style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          ]),
        ]),
      ),
      Container(
        margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Row(children: [
          Expanded(child: _dateChip('📅', tr('من', 'From'), '${lv['date_from'] ?? ''}'.split(' ').first)),
          const Icon(Icons.arrow_forward_rounded, size: 16, color: Mgmt.slate),
          Expanded(child: Align(alignment: AlignmentDirectional.centerEnd,
              child: _dateChip('🏁', tr('إلى', 'To'), '${lv['date_to'] ?? ''}'.split(' ').first))),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📋', tr('تفاصيل الإجازة', 'Leave details')), _infoRows(info)]),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final actions = (d['actions'] as List?) ?? [];
    final sections = (d['sections'] as List?) ?? [];
    final canEdit = d['can_edit'] == true;
    final isProposal = d['proposal'] != null;
    final isTender = d['tender'] != null;
    final isOrder = d['order'] != null;
    final isFleet = d['fleet'] != null;
    final isCrm = d['crm'] != null;
    final isLeave = d['leave'] != null;
    final richDetail = isProposal || isTender || isOrder || isFleet || isCrm || isLeave;
    final amount = richDetail ? null : d['amount'];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.82, maxChildSize: 0.96, minChildSize: 0.45,
      builder: (_, sc) => Stack(children: [
        ListView(controller: sc, padding: EdgeInsets.zero, children: [
          // ---- header
          Container(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Center(child: Container(width: 42, height: 4,
                  decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
              const SizedBox(height: 14),
              Row(children: [
                Text('${d['icon']} ', style: const TextStyle(fontSize: 18)),
                Expanded(child: Text('${d['title']}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                if (canEdit)
                  Material(
                    color: Colors.white.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(11),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(11),
                      onTap: _busy ? null : _editSheet,
                      child: const Padding(
                        padding: EdgeInsets.all(7),
                        child: Icon(Icons.edit_rounded, color: Colors.white, size: 18)),
                    ),
                  ),
              ]),
              if (d['state'] != null) Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                  decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.12), blurRadius: 6, offset: const Offset(0, 2))]),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 7, height: 7,
                        decoration: BoxDecoration(color: mgmtHex('${d['state_color'] ?? ''}', widget.accent), shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    Text('${d['state']}',
                        style: TextStyle(color: mgmtHex('${d['state_color'] ?? ''}', widget.accent), fontWeight: FontWeight.w900, fontSize: 11.5)),
                  ]),
                ),
              ),
            ]),
          ),
          // ---- professional detail blocks per system
          if (isProposal) _proposalBlock(),
          if (isTender) _tenderBlock(),
          if (isOrder) _orderBlock(),
          if (isFleet) _fleetBlock(),
          if (isCrm) _crmBlock(),
          if (isLeave) _leaveBlock(),
          // ---- amount highlight
          if (amount != null)
            Container(
              margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                  color: widget.accent.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16)),
              child: Row(children: [
                Icon(Icons.payments_rounded, color: widget.accent, size: 20),
                const SizedBox(width: 10),
                Text(tr('القيمة', 'Amount'),
                    style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 12.5)),
                const Spacer(),
                Text('$amount',
                    style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 17)),
              ]),
            ),
          // ---- actions
          if (actions.isNotEmpty) Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 2),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              for (final a in actions)
                SizedBox(
                  height: 42,
                  child: (a as Map)['style'] == 'primary'
                      ? ElevatedButton(
                          style: ElevatedButton.styleFrom(
                              backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                          onPressed: _busy ? null : () => _run(a),
                          child: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                              style: const TextStyle(fontWeight: FontWeight.w800)))
                      : OutlinedButton(
                          style: OutlinedButton.styleFrom(
                              foregroundColor: a['style'] == 'danger' ? Mgmt.red : Mgmt.slate,
                              side: BorderSide(color: a['style'] == 'danger' ? Mgmt.red : Colors.black26),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                          onPressed: _busy ? null : () => _run(a),
                          child: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                              style: const TextStyle(fontWeight: FontWeight.w800))),
                ),
            ]),
          ),
          // ---- reports (pdf viewer / xlsx download)
          _reportsCard(),
          // ---- line items
          _linesCard(),
          // ---- professional grouped sections (rich blocks replace these)
          if (!richDetail) for (final s in sections) _sectionCard(s as Map),
          // fallback flat list if the server sent no sections
          if (!richDetail && sections.isEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 0),
              child: Column(children: [
                for (final f in (d['fields'] as List? ?? [])) _fieldRow(f as Map),
              ]),
            ),
          const SizedBox(height: 26),
        ]),
        if (_busy)
          const Positioned.fill(child: ColoredBox(color: Color(0x11000000),
              child: Center(child: CircularProgressIndicator()))),
      ]),
    );
  }
}

/// A professional edit form for the whitelisted fields of one record. The
/// server decides which fields are editable and enforces the ACL again on save.
class _EditSheet extends StatefulWidget {
  const _EditSheet({
    required this.appKey,
    required this.id,
    required this.accent,
    required this.title,
    required this.editable,
  });
  final String appKey;
  final int id;
  final Color accent;
  final String title;
  final List<Map> editable;

  @override
  State<_EditSheet> createState() => _EditSheetState();
}

class _EditSheetState extends State<_EditSheet> {
  final Map<String, dynamic> _vals = {};
  final Map<String, TextEditingController> _ctrls = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    for (final f in widget.editable) {
      final name = '${f['name']}';
      final t = '${f['type']}';
      _vals[name] = f['value'];
      if (t == 'char' || t == 'text' || t == 'float' || t == 'monetary' || t == 'integer') {
        _ctrls[name] = TextEditingController(text: f['value'] == null ? '' : '${f['value']}');
      }
    }
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate(String name, bool withTime) async {
    DateTime init = DateTime.now();
    final cur = _vals[name];
    if (cur is String && cur.isNotEmpty) {
      init = DateTime.tryParse(cur) ?? init;
    }
    final d = await showDatePicker(
        context: context,
        initialDate: init,
        firstDate: DateTime(2015),
        lastDate: DateTime(2100));
    if (d == null) return;
    var out = d;
    if (withTime) {
      final t = await showTimePicker(
          context: context, initialTime: TimeOfDay.fromDateTime(init));
      if (t != null) {
        out = DateTime(d.year, d.month, d.day, t.hour, t.minute);
      }
    }
    final s = withTime
        ? '${out.toIso8601String().substring(0, 16).replaceFirst('T', ' ')}:00'
        : out.toIso8601String().substring(0, 10);
    setState(() => _vals[name] = s);
  }

  Future<void> _save() async {
    // pull text controllers into the value map
    for (final f in widget.editable) {
      final name = '${f['name']}';
      final t = '${f['type']}';
      if (_ctrls.containsKey(name)) {
        final raw = _ctrls[name]!.text.trim();
        if (t == 'float' || t == 'monetary') {
          _vals[name] = double.tryParse(raw) ?? 0;
        } else if (t == 'integer') {
          _vals[name] = int.tryParse(raw) ?? 0;
        } else {
          _vals[name] = raw;
        }
      }
    }
    setState(() => _busy = true);
    try {
      await context
          .read<AuthProvider>()
          .api
          .managementWrite(widget.appKey, widget.id, _vals);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم الحفظ', '✅ Saved')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6, top: 14),
        child: Text(t,
            style: const TextStyle(
                fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.slate)),
      );

  InputDecoration _dec() => InputDecoration(
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: widget.accent, width: 1.6)),
      );

  Widget _field(Map f) {
    final name = '${f['name']}';
    final t = '${f['type']}';
    if (t == 'many2one' || t == 'selection') {
      final opts = ((f['options'] as List?) ?? const []).cast<Map>();
      final cur = _vals[name];
      return DropdownButtonFormField(
        value: opts.any((o) => o['v'] == cur) ? cur : null,
        isExpanded: true,
        decoration: _dec(),
        items: [
          for (final o in opts)
            DropdownMenuItem(value: o['v'], child: Text('${o['l']}', overflow: TextOverflow.ellipsis)),
        ],
        onChanged: (v) => _vals[name] = v,
      );
    }
    if (t == 'date' || t == 'datetime') {
      return InkWell(
        onTap: () => _pickDate(name, t == 'datetime'),
        child: InputDecorator(
          decoration: _dec(),
          child: Row(children: [
            Icon(Icons.event_rounded, size: 18, color: widget.accent),
            const SizedBox(width: 8),
            Text('${_vals[name] ?? tr('اختر التاريخ', 'Pick a date')}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
        ),
      );
    }
    if (t == 'boolean') {
      return SwitchListTile(
        contentPadding: EdgeInsets.zero,
        activeColor: widget.accent,
        value: _vals[name] == true,
        title: Text(tr('نعم', 'Yes')),
        onChanged: (v) => setState(() => _vals[name] = v),
      );
    }
    final isNum = t == 'float' || t == 'monetary' || t == 'integer';
    return TextField(
      controller: _ctrls[name],
      keyboardType: isNum ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      maxLines: t == 'text' ? 3 : 1,
      decoration: _dec(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.95,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(20, 12, 20, 20), children: [
          Center(child: Container(width: 40, height: 4,
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 14),
          Row(children: [
            Icon(Icons.edit_note_rounded, color: widget.accent),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('تعديل السجل', 'Edit record'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))),
          ]),
          Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Mgmt.slate, fontSize: 12.5)),
          for (final f in widget.editable) ...[
            _label('${f['label']}'),
            _field(f),
          ],
          const SizedBox(height: 22),
          SizedBox(
            height: 48,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                  backgroundColor: widget.accent, foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : _save,
              icon: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_rounded),
              label: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            ),
          ),
        ]),
      ),
    );
  }
}

/// A professional create form for a new quotation (proposal). Fetches the
/// pickers (customers, service types, modes) from the server, then posts the
/// chosen values. Returns {id, ref, title} on success.
class _ProposalCreateSheet extends StatefulWidget {
  const _ProposalCreateSheet({required this.accent});
  final Color accent;
  @override
  State<_ProposalCreateSheet> createState() => _ProposalCreateSheetState();
}

class _ProposalCreateSheetState extends State<_ProposalCreateSheet> {
  Map<String, dynamic>? _meta;
  bool _loading = true, _busy = false;
  String? _err;

  int? _partnerId, _serviceTypeId;
  String? _proposalDate, _expireDate, _mobDate, _mode;
  final _site = TextEditingController();
  final _period = TextEditingController();
  final _margin = TextEditingController(text: '20');
  final _notes = TextEditingController();

  @override
  void initState() {
    super.initState();
    _proposalDate = DateTime.now().toIso8601String().substring(0, 10);
    _load();
  }

  @override
  void dispose() {
    _site.dispose(); _period.dispose(); _margin.dispose(); _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.managementProposalMeta();
      if (mounted) setState(() { _meta = m; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  Future<void> _pick(String which) async {
    final now = DateTime.now();
    final cur = which == 'p' ? _proposalDate : (which == 'e' ? _expireDate : _mobDate);
    final init = (cur != null && cur.isNotEmpty) ? DateTime.tryParse(cur) ?? now : now;
    final d = await showDatePicker(
        context: context, initialDate: init,
        firstDate: DateTime(2015), lastDate: DateTime(2100));
    if (d == null) return;
    final s = d.toIso8601String().substring(0, 10);
    setState(() {
      if (which == 'p') _proposalDate = s;
      else if (which == 'e') _expireDate = s;
      else _mobDate = s;
    });
  }

  Future<void> _pickCustomer() async {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _PickerSheet(title: tr('اختر العميل', 'Select customer'), options: list, accent: widget.accent),
    );
    if (chosen != null) setState(() => _partnerId = chosen);
  }

  String? _customerLabel() {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final m = list.where((e) => e['v'] == _partnerId);
    return m.isEmpty ? null : '${m.first['l']}';
  }

  Future<void> _submit() async {
    if (_partnerId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('اختر العميل أولًا', 'Select a customer first')), backgroundColor: Mgmt.red));
      return;
    }
    setState(() => _busy = true);
    try {
      final vals = <String, dynamic>{
        'partner_id': _partnerId,
        if (_serviceTypeId != null) 'service_type_id': _serviceTypeId,
        if (_proposalDate != null) 'proposal_date': _proposalDate,
        if (_expireDate != null) 'expire_date': _expireDate,
        if (_mobDate != null) 'mobilization_date': _mobDate,
        if (_site.text.trim().isNotEmpty) 'service_site': _site.text.trim(),
        if (_mode != null) 'mode': _mode,
        if (_period.text.trim().isNotEmpty) 'proposal_period': _period.text.trim(),
        if (_margin.text.trim().isNotEmpty) 'target_margin_pct': _margin.text.trim(),
        if (_notes.text.trim().isNotEmpty) 'notes': _notes.text.trim(),
      };
      final res = await context.read<AuthProvider>().api.managementProposalCreate(vals);
      if (mounted) Navigator.pop(context, res);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true, filled: true, fillColor: Mgmt.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(2, 14, 2, 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
      );

  Widget _tap(String? value, String hint, IconData icon, VoidCallback onTap) => InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(icon, size: 18, color: widget.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(value ?? hint,
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 13,
                    color: value == null ? Mgmt.slate : Mgmt.ink,
                    fontWeight: value == null ? FontWeight.w500 : FontWeight.w700))),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final types = ((_meta?['service_types'] as List?) ?? const []).cast<Map>();
    final modes = ((_meta?['modes'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            Center(child: Container(width: 42, height: 4,
                decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 12),
            Row(children: [
              const Text('📊 ', style: TextStyle(fontSize: 18)),
              Expanded(child: Text(tr('عرض سعر جديد', 'New quotation'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
              IconButton(onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _err != null
                  ? Center(child: Padding(padding: const EdgeInsets.all(30),
                      child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
                  : ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                      _label('${tr('العميل', 'Customer')} *'),
                      _tap(_customerLabel(), tr('اختر العميل', 'Select customer'), Icons.business_rounded, _pickCustomer),
                      _label(tr('نوع الخدمة', 'Service type')),
                      _dropdown(types, _serviceTypeId, (v) => setState(() => _serviceTypeId = v), tr('اختر النوع', 'Select type')),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ العرض', 'Proposal date')),
                          _tap(_proposalDate, tr('اختر', 'Pick'), Icons.event_rounded, () => _pick('p')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ الانتهاء', 'Expiry date')),
                          _tap(_expireDate, tr('اختر', 'Pick'), Icons.event_busy_rounded, () => _pick('e')),
                        ])),
                      ]),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ المباشرة', 'Mobilization')),
                          _tap(_mobDate, tr('اختر', 'Pick'), Icons.flag_rounded, () => _pick('m')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('المدة (شهور)', 'Period (months)')),
                          TextField(controller: _period, keyboardType: TextInputType.number, decoration: _dec('0')),
                        ])),
                      ]),
                      _label(tr('موقع الخدمة', 'Service site')),
                      TextField(controller: _site, decoration: _dec(tr('العنوان / الموقع', 'Address / site'))),
                      if (modes.isNotEmpty) ...[
                        _label(tr('نمط الفوترة', 'Billing mode')),
                        _dropdownStr(modes, _mode, (v) => setState(() => _mode = v), tr('اختر', 'Select')),
                      ],
                      _label(tr('هامش الربح المستهدف %', 'Target margin %')),
                      TextField(controller: _margin, keyboardType: TextInputType.number, decoration: _dec('20')),
                      _label(tr('ملاحظات', 'Notes')),
                      TextField(controller: _notes, maxLines: 3, decoration: _dec(tr('ملاحظات إضافية…', 'Extra notes…'))),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                              backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                          onPressed: _busy ? null : _submit,
                          icon: _busy
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.add_rounded),
                          label: Text(tr('إنشاء العرض', 'Create quotation'),
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                        ),
                      ),
                    ]),
        ),
      ]),
    );
  }

  Widget _dropdown(List<Map> opts, int? value, ValueChanged<int?> onChanged, String hint) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<int>(
            value: value, isExpanded: true, hint: Text(hint, style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: o['v'] as int, child: Text('${o['l']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)))],
            onChanged: onChanged,
          ),
        ),
      );

  Widget _dropdownStr(List<Map> opts, String? value, ValueChanged<String?> onChanged, String hint) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: value, isExpanded: true, hint: Text(hint, style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: '${o['v']}', child: Text('${o['l']}', style: const TextStyle(fontSize: 13)))],
            onChanged: onChanged,
          ),
        ),
      );
}

/// A searchable single-select bottom sheet for long option lists (customers).
class _PickerSheet extends StatefulWidget {
  const _PickerSheet({required this.title, required this.options, required this.accent});
  final String title;
  final List<Map> options;
  final Color accent;
  @override
  State<_PickerSheet> createState() => _PickerSheetState();
}

class _PickerSheetState extends State<_PickerSheet> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final filtered = _q.isEmpty
        ? widget.options
        : widget.options.where((o) => '${o['l']}'.toLowerCase().contains(_q.toLowerCase())).toList();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.8, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Expanded(child: Text(widget.title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true,
            onChanged: (v) => setState(() => _q = v),
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: ListView.separated(
            controller: sc,
            itemCount: filtered.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
            itemBuilder: (_, i) => ListTile(
              title: Text('${filtered[i]['l']}', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
              onTap: () => Navigator.pop(context, filtered[i]['v'] as int),
            ),
          ),
        ),
      ]),
    );
  }
}
