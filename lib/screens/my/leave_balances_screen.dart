import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';

/// أرصدة إجازات الموظف الحالي ومستحقاتها — شاشة خدمة ذاتية داخل «My».
class LeaveBalancesScreen extends StatefulWidget {
  final Color accent;
  const LeaveBalancesScreen({super.key, this.accent = const Color(0xFF0F2A56)});
  @override
  State<LeaveBalancesScreen> createState() => _LeaveBalancesScreenState();
}

class _LeaveBalancesScreenState extends State<LeaveBalancesScreen> {
  static const _ink = Color(0xFF1E293B);
  static const _slate = Color(0xFF64748B);
  Map<String, dynamic>? _d;
  String? _error;

  Color get _c => widget.accent;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final d = await context.read<AuthProvider>().api.myLeaveBalances();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _c,
        foregroundColor: Colors.white,
        title: Text(tr('أرصدة إجازاتي', 'My leave balances')),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        color: _c,
        child: _error != null
            ? ListView(children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 120, 24, 24),
                  child: Column(children: [
                    const Icon(Icons.cloud_off_rounded, size: 44, color: _slate),
                    const SizedBox(height: 12),
                    Text('$_error', textAlign: TextAlign.center,
                        style: const TextStyle(color: _slate, fontSize: 12)),
                  ]),
                )
              ])
            : _d == null
                ? Center(child: CircularProgressIndicator(color: _c))
                : _body(_d!),
      ),
    );
  }

  Widget _body(Map d) {
    final bals = ((d['balances'] as List?) ?? const []).cast<Map>();
    final s = (d['summary'] as Map?) ?? const {};
    return ListView(padding: const EdgeInsets.all(16), children: [
      _summaryCard(s),
      const SizedBox(height: 14),
      if (bals.isEmpty)
        Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
              child: Text(tr('لا توجد أرصدة بعد', 'No balances yet'),
                  style: const TextStyle(color: _slate))),
        )
      else
        for (final b in bals) _balanceCard(b),
    ]);
  }

  Widget _summaryCard(Map s) {
    final cur = '${s['currency'] ?? ''}';
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [_c, _c.withValues(alpha: 0.78)]),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(children: [
        _summaryCell(tr('إجمالي المتبقّي', 'Total remaining'),
            '${s['total_remaining'] ?? 0}', tr('يوم', 'days')),
        Container(width: 1, height: 42, color: Colors.white24),
        _summaryCell(tr('القيمة النقدية', 'Cash value'),
            '${s['total_cash'] ?? 0}', cur),
        Container(width: 1, height: 42, color: Colors.white24),
        _summaryCell(tr('الأنواع', 'Types'), '${s['types'] ?? 0}', ''),
      ]),
    );
  }

  Widget _summaryCell(String label, String value, String unit) => Expanded(
        child: Column(children: [
          Text(value,
              style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)),
          const SizedBox(height: 2),
          Text(unit,
              style: const TextStyle(color: Colors.white70, fontSize: 10)),
          const SizedBox(height: 4),
          Text(label,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 11)),
        ]),
      );

  Widget _balanceCard(Map b) {
    final remaining = (b['remaining'] ?? 0) as num;
    final Color stripe = remaining <= 0
        ? const Color(0xFFDC2626)
        : remaining <= 5
            ? const Color(0xFFD97706)
            : const Color(0xFF16A34A);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          leading: Container(width: 6, height: 42, color: stripe),
          title: Text('${b['leave_type'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
          subtitle: Text(
              '${tr('متبقّي', 'Remaining')}: ${b['remaining']} ${tr('يوم', 'd')} · '
              '${tr('نقدي', 'Cash')}: ${b['cash_value']} ${b['currency'] ?? ''}',
              style: const TextStyle(color: _slate, fontSize: 12)),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          children: [
            _kv(tr('الممنوح', 'Granted'), '${b['granted']}'),
            _kv(tr('المستحق', 'Accrued'), '${b['accrued']}'),
            _kv(tr('المرحّل', 'Carried-in'), '${b['carried_in']}'),
            _kv(tr('التعديلات', 'Adjustments'), '${b['adjust']}'),
            _kv(tr('المأخوذ', 'Taken'), '${b['taken']}'),
            _kv(tr('المصروف', 'Encashed'), '${b['encashed']}'),
            _kv(tr('الأجر اليومي', 'Daily rate'), '${b['daily_rate']} ${b['currency'] ?? ''}'),
            const Divider(),
            if (((b['movements'] as List?) ?? const []).isNotEmpty) ...[
              Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text(tr('الحركات', 'Movements'),
                      style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 12))),
              const SizedBox(height: 6),
              for (final m in ((b['movements'] as List).cast<Map>()))
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(children: [
                    Expanded(flex: 3, child: Text('${m['date']}', style: const TextStyle(fontSize: 11, color: _slate))),
                    Expanded(flex: 4, child: Text('${m['type']}', style: const TextStyle(fontSize: 11, color: _ink))),
                    Expanded(flex: 2, child: Text('${m['days']}', textAlign: TextAlign.end, style: const TextStyle(fontSize: 11, color: _ink))),
                  ]),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: _slate, fontSize: 12.5)),
          Text(v, style: const TextStyle(color: _ink, fontWeight: FontWeight.w700, fontSize: 12.5)),
        ]),
      );
}
