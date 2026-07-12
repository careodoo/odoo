import 'package:flutter/material.dart';
import '../models/models.dart';
import '../screens/notifications_screen.dart';

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
  const StatCard({super.key, required this.label, required this.value, required this.color, this.icon});
  final String label;
  final int value;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
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
  }
}

/// The worker's own KPI row (open / in-progress / done / overdue).
class MyStatsRow extends StatelessWidget {
  const MyStatsRow({super.key, required this.counts});
  final Counts counts;

  @override
  Widget build(BuildContext context) {
    final items = [
      ('مفتوحة', counts.open, const Color(0xFF2F6DF6), Icons.inbox),
      ('جارية', counts.inProgress, const Color(0xFFF7A23B), Icons.timelapse),
      ('منجزة', counts.done, const Color(0xFF16794A), Icons.check_circle),
      ('متأخرة', counts.overdue, const Color(0xFFE5484D), Icons.warning_amber),
    ];
    return Row(
      children: [
        for (final it in items) ...[
          Expanded(child: StatCard(label: it.$1, value: it.$2, color: it.$3, icon: it.$4)),
          if (it != items.last) const SizedBox(width: 8),
        ]
      ],
    );
  }
}
