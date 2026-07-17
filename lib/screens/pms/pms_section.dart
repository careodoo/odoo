import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';

/// Icons for the section codes the API advertises. Kept here rather than sent
/// from the server: the server names the section, the app decides how it looks.
const Map<String, IconData> kPmsSectionIcons = {
  'materials': Icons.inventory_2_rounded,
  'deliveries': Icons.receipt_long_rounded,
  'supplies': Icons.local_shipping_rounded,
  'petty': Icons.payments_rounded,
  'requests': Icons.description_rounded,
  'team': Icons.groups_rounded,
  'attendance': Icons.schedule_rounded,
  'timesheet': Icons.timer_rounded,
  'assets': Icons.precision_manufacturing_rounded,
  'fuel': Icons.local_gas_station_rounded,
  'compliance': Icons.verified_user_rounded,
  'finance': Icons.account_balance_rounded,
  'contracts': Icons.assignment_rounded,
  'performance': Icons.trending_up_rounded,
};

const Map<String, Color> kPmsSectionColors = {
  'materials': Color(0xFF0891B2),
  'deliveries': Color(0xFF6366F1),
  'supplies': Color(0xFF0EA5E9),
  'petty': Color(0xFF16A34A),
  'requests': Color(0xFF8B5CF6),
  'team': Color(0xFF0D9488),
  'attendance': Color(0xFF2F6DF6),
  'timesheet': Color(0xFF7C3AED),
  'assets': Color(0xFF64748B),
  'fuel': Color(0xFFF7A23B),
  'compliance': Color(0xFFE5484D),
  'finance': Color(0xFF15803D),
  'contracts': Color(0xFF9333EA),
  'performance': Color(0xFF0891B2),
};

/// One project section — the same shape the portal shows, rendered natively.
/// Every section returns {stats, rows}, so one screen serves all fourteen.
class PmsSectionScreen extends StatefulWidget {
  const PmsSectionScreen({
    super.key,
    required this.projectId,
    required this.code,
    required this.label,
  });

  final int projectId;
  final String code;
  final String label;

  @override
  State<PmsSectionScreen> createState() => _PmsSectionScreenState();
}

class _PmsSectionScreenState extends State<PmsSectionScreen> {
  Future<Map<String, dynamic>>? _f;
  String _q = '';

  Color get _c => kPmsSectionColors[widget.code] ?? Pms.violet;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.pmsSection(widget.projectId, widget.code);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: _c, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.label, overflow: TextOverflow.ellipsis),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [
                const SizedBox(height: 100),
                Center(child: Padding(
                  padding: const EdgeInsets.all(30),
                  child: Text('${snap.error}', textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey)),
                )),
              ]);
            }
            final d = snap.data ?? const {};
            final stats = (d['stats'] as Map?) ?? const {};
            final all = (d['rows'] as List?) ?? const [];
            final rows = _q.isEmpty
                ? all
                : all.where((r) {
                    final m = r as Map;
                    final hay = '${m['title'] ?? ''} ${m['subtitle'] ?? ''} '
                        '${(m['badges'] as List?)?.join(' ') ?? ''}'.toLowerCase();
                    return hay.contains(_q.toLowerCase());
                  }).toList();
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              if (stats.isNotEmpty) _statsBand(stats),
              if (all.length > 8) ...[
                const SizedBox(height: 10),
                TextField(
                  onChanged: (v) => setState(() => _q = v),
                  decoration: InputDecoration(
                    hintText: tr('ابحث…', 'Search…'),
                    prefixIcon: const Icon(Icons.search_rounded, size: 19),
                    isDense: true, filled: true, fillColor: Colors.white,
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
              ],
              const SizedBox(height: 10),
              if (d['empty'] != null && all.isEmpty)
                _empty('${d['empty']}')
              else if (all.isEmpty)
                _empty(tr('لا سجلات في هذا القسم.', 'Nothing in this section yet.'))
              else if (rows.isEmpty)
                _empty(tr('لا نتائج للبحث.', 'No matches.'))
              else ...[
                Padding(
                  padding: const EdgeInsets.only(bottom: 6, right: 2),
                  child: Text(
                      _q.isEmpty
                          ? tr('${all.length} سجل', '${all.length} records')
                          : tr('${rows.length} من ${all.length}', '${rows.length} of ${all.length}'),
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500)),
                ),
                for (final r in rows) _row(r as Map),
              ],
            ]);
          },
        ),
      ),
    );
  }

  Widget _statsBand(Map stats) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_c, Color.lerp(_c, Colors.black, 0.3)!],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: _c.withValues(alpha: 0.3), blurRadius: 10, offset: const Offset(0, 4))],
        ),
        child: Row(children: [
          for (final e in stats.entries) ...[
            Expanded(child: Column(children: [
              Text('${e.value}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              Text('${e.key}',
                  maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.75),
                      fontSize: 8.5, fontWeight: FontWeight.w700, height: 1.2)),
            ])),
            if (e.key != stats.keys.last)
              Container(width: 1, height: 24, color: Colors.white.withValues(alpha: 0.15)),
          ],
        ]),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 60),
        child: Center(child: Column(children: [
          Icon(kPmsSectionIcons[widget.code] ?? Icons.inbox_rounded,
              size: 40, color: Colors.grey.shade300),
          const SizedBox(height: 10),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 30),
            child: Text(t, textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5, height: 1.6)),
          ),
        ])),
      );

  /// Row state colours. 'expired'/'soon' come from the compliance section and
  /// must read as alarming; everything else is neutral.
  (Color, Color) _stateColors(String? state) {
    switch (state) {
      case 'expired':
        return (const Color(0xFFE5484D), Colors.white);
      case 'soon':
        return (const Color(0xFFF7A23B), Colors.white);
      case 'ok':
      case 'done':
      case 'received':
      case 'closed':
        return (const Color(0xFF16A34A), Colors.white);
      case 'open':
        return (const Color(0xFF16A34A), Colors.white);
      case 'draft':
        return (Colors.grey.shade300, Colors.black87);
      default:
        return (_c.withValues(alpha: 0.12), _c);
    }
  }

  Widget _row(Map r) {
    final badges = (r['badges'] as List?) ?? const [];
    final sc = _stateColors(r['state'] as String?);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (r['image'] != null) ...[
            CircleAvatar(
              radius: 18,
              backgroundColor: _c.withValues(alpha: 0.1),
              backgroundImage: NetworkImage('${r['image']}'),
              onBackgroundImageError: (_, __) {},
              child: null,
            ),
            const SizedBox(width: 9),
          ] else ...[
            Container(
              width: 36, height: 36, alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: _c.withValues(alpha: 0.09), borderRadius: BorderRadius.circular(11)),
              child: Icon(kPmsSectionIcons[widget.code] ?? Icons.circle, size: 17, color: _c),
            ),
            const SizedBox(width: 9),
          ],
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['title']}',
                maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            if (r['subtitle'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text('${r['subtitle']}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
              ),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (r['value'] != null)
              Row(crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic, children: [
                Text('${r['value']}',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _c)),
                if (r['value_label'] != null) ...[
                  const SizedBox(width: 2),
                  Text('${r['value_label']}',
                      style: TextStyle(fontSize: 8, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
                ],
              ]),
            if (r['state_label'] != null) ...[
              const SizedBox(height: 3),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: sc.$1, borderRadius: BorderRadius.circular(6)),
                child: Text('${r['state_label']}',
                    style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: sc.$2)),
              ),
            ],
          ]),
        ]),
        if (badges.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 5, runSpacing: 5, children: [
            for (final b in badges)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                    color: Colors.grey.withValues(alpha: 0.09),
                    borderRadius: BorderRadius.circular(7)),
                child: Text('$b',
                    style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: Colors.grey.shade700)),
              ),
          ]),
        ],
      ]),
    );
  }
}
