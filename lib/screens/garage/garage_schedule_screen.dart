import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_home.dart' show kGrgNavy, kGrgBg, kGrgInk, kGrgGrey, grgNum;
import 'garage_requests.dart' show GarageRequestDetail;

/// شاشة متابعة مواعيد الصيانة في التطبيق — مؤشّرات + متأخرة/هذا الأسبوع/قريبة.
class GarageScheduleScreen extends StatefulWidget {
  const GarageScheduleScreen({super.key});
  @override
  State<GarageScheduleScreen> createState() => _GarageScheduleScreenState();
}

class _GarageScheduleScreenState extends State<GarageScheduleScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map<String, dynamic>? _d;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await _api.grgSchedule();
      if (mounted) setState(() => _d = d);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d ?? const {};
    final kpi = Map<String, dynamic>.from((d['kpi'] as Map?) ?? const {});
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('متابعة المواعيد', 'Service schedule')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 14, 12, 28), children: [
                _kpis(kpi),
                const SizedBox(height: 16),
                _section(tr('متأخرة عن الموعد', 'Overdue'), '⏰', const Color(0xFFDC3030), List.from((d['overdue'] as List?) ?? const [])),
                _section(tr('هذا الأسبوع', 'This week'), '📅', const Color(0xFFE08A00), List.from((d['this_week'] as List?) ?? const [])),
                _section(tr('خلال 30 يومًا', 'Within 30 days'), '🗓️', const Color(0xFF0E8A8A), List.from((d['soon'] as List?) ?? const [])),
              ]),
            ),
    );
  }

  Widget _kpis(Map<String, dynamic> k) {
    final tiles = <(String, dynamic, Color)>[
      (tr('مجدولة', 'Scheduled'), k['scheduled'], const Color(0xFF2563EB)),
      (tr('متأخرة', 'Overdue'), k['overdue'], const Color(0xFFDC3030)),
      (tr('هذا الأسبوع', 'This week'), k['this_week'], const Color(0xFFE08A00)),
      (tr('خلال 30', 'In 30d'), k['soon'], const Color(0xFF0E8A8A)),
      (tr('بلا موعد', 'No date'), k['no_date'], const Color(0xFF64748B)),
    ];
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 1.05,
      children: tiles
          .map((t) => Container(
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border(top: BorderSide(color: t.$3, width: 3), left: const BorderSide(color: Color(0xFFE2E8F0)), right: const BorderSide(color: Color(0xFFE2E8F0)), bottom: const BorderSide(color: Color(0xFFE2E8F0)))),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text(grgNum(t.$2), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: t.$3)),
                  Text(t.$1, style: const TextStyle(color: kGrgGrey, fontSize: 10.5, fontWeight: FontWeight.w600)),
                ]),
              ))
          .toList(),
    );
  }

  Widget _section(String title, String icon, Color c, List rows) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
          child: Text('$icon $title (${rows.length})', style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 13.5)),
        ),
        if (rows.isEmpty)
          const Padding(padding: EdgeInsets.fromLTRB(14, 0, 14, 12), child: Text('—', style: TextStyle(color: kGrgGrey)))
        else
          ...rows.map((x) {
            final r = Map<String, dynamic>.from(x as Map);
            final days = (r['days'] as num?)?.toInt() ?? 0;
            return InkWell(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => GarageRequestDetail(id: r['id'] as int))),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                child: Row(children: [
                  Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${r['vehicle']}', style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk, fontSize: 13)),
                    Text('${r['type']} · ${r['next_date']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kGrgGrey, fontSize: 11.5)),
                  ])),
                  Text(days < 0 ? tr('متأخرة ${-days}', '${-days}d late') : tr('$days يوم', '${days}d'),
                      style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: days < 0 ? const Color(0xFFDC3030) : kGrgInk)),
                ]),
              ),
            );
          }),
      ]),
    );
  }
}
