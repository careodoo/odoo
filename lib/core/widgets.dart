import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../core/i18n.dart';
import '../screens/notifications_screen.dart';
import '../screens/workorders_screen.dart';

/// Shared language picker — lists every supported UI language.
void showLanguagePicker(BuildContext context, {VoidCallback? onChanged}) {
  showModalBottomSheet(
    context: context, backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
      const SizedBox(height: 10),
      Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))),
      Padding(padding: const EdgeInsets.all(14), child: Text(tr('اختر اللغة', 'Choose language'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))),
      for (final l in context.read<LangProvider>().languages)
        ListTile(
          title: Text(l[1], style: const TextStyle(fontWeight: FontWeight.w600)),
          trailing: gLang == l[0] ? const Icon(Icons.check_circle_rounded, color: Color(0xFF2F6DF6)) : null,
          onTap: () { context.read<LangProvider>().setLang(l[0]); Navigator.pop(context); onChanged?.call(); },
        ),
      const SizedBox(height: 8),
    ])),
  );
}

/// Work-order state → colour + Arabic/English label (shared across screens).
const Map<String, Color> kWoStateColor = {
  'new': Color(0xFF64748B),
  'assigned': Color(0xFF2F6DF6),
  'in_progress': Color(0xFFF59E0B),
  'hold': Color(0xFF9333EA),
  'done': Color(0xFF16A34A),
  'verified': Color(0xFF0E7490),
  'cancelled': Color(0xFFE5484D),
};
String woStateLabel(String s) => const {
      'new': 'جديد', 'assigned': 'مُسنَد', 'in_progress': 'قيد التنفيذ',
      'hold': 'معلّق', 'done': 'منجز', 'verified': 'مُعتمد', 'cancelled': 'ملغى',
    }[s] ?? s;

/// A coloured state pill.
class WoStateBadge extends StatelessWidget {
  const WoStateBadge(this.state, {super.key});
  final String state;
  @override
  Widget build(BuildContext context) {
    final c = kWoStateColor[state] ?? const Color(0xFF64748B);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20)),
      child: Text(woStateLabel(state), style: TextStyle(fontSize: 12, color: c, fontWeight: FontWeight.w800)),
    );
  }
}

/// App-bar bell with an unread badge.
class NotifBell extends StatelessWidget {
  const NotifBell({super.key, required this.unread});
  final int unread;
  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        IconButton(
          icon: const Icon(Icons.notifications_outlined),
          onPressed: () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => const NotificationsScreen())),
        ),
        if (unread > 0)
          Positioned(
            top: 8, right: 6,
            child: Container(
              padding: const EdgeInsets.all(4),
              constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
              decoration: const BoxDecoration(color: Color(0xFFE5484D), shape: BoxShape.circle),
              child: Text('$unread',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800)),
            ),
          ),
      ],
    );
  }
}

/// A compact KPI card used across every service face.
class StatCard extends StatelessWidget {
  const StatCard({super.key, required this.label, required this.value, required this.color, this.icon, this.onTap});
  final String label;
  final int value;
  final Color color;
  final IconData? icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Column(
        children: [
          if (icon != null) Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          Text('$value',
              style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.w900)),
          Text(label, style: const TextStyle(fontSize: 12), textAlign: TextAlign.center),
        ],
      ),
    );
    if (onTap == null) return card;
    return InkWell(borderRadius: BorderRadius.circular(14), onTap: onTap, child: card);
  }
}

/// The worker's own KPI row (open / in-progress / done / overdue).
class MyStatsRow extends StatelessWidget {
  const MyStatsRow({super.key, required this.counts});
  final Counts counts;

  @override
  Widget build(BuildContext context) {
    final items = [
      (tr('مفتوحة', 'Open'), counts.open, const Color(0xFF2F6DF6), Icons.inbox),
      (tr('جارية', 'Active'), counts.inProgress, const Color(0xFFF7A23B), Icons.timelapse),
      (tr('منجزة', 'Done'), counts.done, const Color(0xFF16794A), Icons.check_circle),
      (tr('متأخرة', 'Overdue'), counts.overdue, const Color(0xFFE5484D), Icons.warning_amber),
    ];
    void open() => Navigator.push(context, MaterialPageRoute(builder: (_) => const WorkOrdersScreen()));
    return Row(
      children: [
        for (final it in items) ...[
          Expanded(child: StatCard(label: it.$1, value: it.$2, color: it.$3, icon: it.$4, onTap: open)),
          if (it != items.last) const SizedBox(width: 8),
        ]
      ],
    );
  }
}
