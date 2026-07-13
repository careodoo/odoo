import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client contracts sourced from the Experience module — details + downloadable
/// copies (fetched with the Bearer token and shared/opened).
class ContractsScreen extends StatefulWidget {
  const ContractsScreen({super.key});
  @override
  State<ContractsScreen> createState() => _ContractsScreenState();
}

class _ContractsScreenState extends State<ContractsScreen> {
  late Future<List<dynamic>> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientContracts();

  static const _stateColor = {
    'draft': Color(0xFF64748B), 'submit': Color(0xFF2F6DF6), 'valid': Color(0xFF16A34A),
    'under_renewal': Color(0xFFF59E0B), 'expired': Color(0xFFE11D48), 'terminated': Color(0xFF94A3B8),
  };

  Future<void> _openCopy(Map copy) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      final tok = await api.token;
      final url = api.contractCopyUrl('${copy['url']}');
      final res = await http.get(Uri.parse(url), headers: tok != null ? {'Authorization': 'Bearer $tok'} : null);
      final dir = await getTemporaryDirectory();
      final name = '${copy['name'] ?? 'contract'}'.replaceAll(RegExp(r'[^\w.\-]'), '_');
      final f = File('${dir.path}/$name');
      await f.writeAsBytes(res.bodyBytes);
      await Share.shareXFiles([XFile(f.path)]);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح النسخة', 'Cannot open copy'))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('العقود', 'Contracts'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snap.hasError) return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)))]);
            final list = snap.data ?? const [];
            if (list.isEmpty) return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا عقود.', 'No contracts.'), style: TextStyle(color: cs.outline)))]);
            return ListView.builder(
              padding: const EdgeInsets.all(14),
              itemCount: list.length,
              itemBuilder: (_, i) => _card(list[i] as Map, cs),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map c, ColorScheme cs) {
    final sc = _stateColor[c['state_raw']] ?? const Color(0xFF64748B);
    final copies = (c['copies'] as List?) ?? const [];
    final gs = (c['guarantees'] as List?) ?? const [];
    Widget row(String l, dynamic v) => (v == null || '$v'.isEmpty || '$v' == 'null') ? const SizedBox.shrink()
        : Padding(padding: const EdgeInsets.symmetric(vertical: 2.5), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 90, child: Text(l, style: TextStyle(color: cs.outline, fontSize: 12.5))),
            Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5))),
          ]));
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.description, color: Color(0xFF0B6EA8)),
        const SizedBox(width: 8),
        Expanded(child: Text('${c['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
        Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(color: sc.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
            child: Text('${c['state'] ?? ''}', style: TextStyle(color: sc, fontSize: 11, fontWeight: FontWeight.w800))),
      ]),
      const Divider(height: 18),
      row(tr('المرجع', 'Ref'), c['ref']),
      row(tr('العميل', 'Client'), c['partner']),
      row(tr('النوع', 'Type'), c['type']),
      row(tr('القيمة', 'Value'), '${c['amount'] ?? 0} ${c['currency'] ?? ''}'),
      row(tr('المدة', 'Period'), '${c['period_months'] ?? 0} ${tr('شهر', 'months')}'),
      row(tr('العمالة', 'Labor'), c['labor']),
      row(tr('البداية', 'Start'), '${c['start'] ?? ''}'.split('T').first),
      row(tr('الانتهاء', 'Expiry'), '${c['expire'] ?? ''}'.split('T').first),
      row(tr('المشروع', 'Project'), c['project']),
      if ((c['days_to_expiry'] ?? 0) is int)
        Padding(padding: const EdgeInsets.only(top: 4), child: Text(
            (c['days_to_expiry'] as int) >= 0 ? '${tr('يتبقى', 'Remaining')} ${c['days_to_expiry']} ${tr('يوم', 'days')}' : tr('منتهٍ', 'Expired'),
            style: TextStyle(color: (c['days_to_expiry'] as int) < 30 ? const Color(0xFFE11D48) : cs.outline, fontSize: 12.5, fontWeight: FontWeight.w700))),
      if (gs.isNotEmpty) ...[
        const Divider(height: 18),
        Text(tr('الكفالات', 'Guarantees'), style: TextStyle(color: cs.outline, fontSize: 12)),
        for (final g in gs) Text('🏦 ${(g as Map)['name'] ?? ''} · ${g['bank'] ?? ''} · ${g['amount'] ?? 0}', style: const TextStyle(fontSize: 12.5)),
      ],
      const SizedBox(height: 10),
      Text(tr('نُسخ العقد', 'Contract copies'), style: TextStyle(color: cs.outline, fontSize: 12)),
      const SizedBox(height: 6),
      if (copies.isEmpty) Text(tr('لا نُسخ مرفقة', 'No copies attached'), style: TextStyle(color: cs.outline, fontSize: 12.5))
      else Wrap(spacing: 8, runSpacing: 8, children: [
        for (final a in copies) OutlinedButton.icon(
          onPressed: _busy ? null : () => _openCopy(a as Map),
          icon: const Icon(Icons.download, size: 16),
          label: Text('${(a as Map)['name'] ?? 'نسخة'}', overflow: TextOverflow.ellipsis)),
      ]),
    ])));
  }
}
