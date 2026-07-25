import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import 'auth.dart';
import '../core/i18n.dart';
import '../screens/notifications_screen.dart';
import '../screens/workorders_screen.dart';

/// A softly pulsing badge — a live "heartbeat" ring behind its child, used to
/// signal real-time figures (people on site now). Respects reduced-motion.
class PulseBadge extends StatefulWidget {
  const PulseBadge({super.key, required this.child, this.color = const Color(0xFF16A34A)});
  final Widget child;
  final Color color;
  @override
  State<PulseBadge> createState() => _PulseBadgeState();
}

class _PulseBadgeState extends State<PulseBadge> with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))..repeat();
  }
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    if (MediaQuery.maybeOf(context)?.disableAnimations ?? false) return widget.child;
    // The child sizes the Stack; the ring overflows via a Positioned.fill +
    // OverflowBox so its animated growth NEVER changes the layout height (that
    // was making the header pulse taller/shorter every cycle).
    return Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
      Positioned.fill(child: IgnorePointer(child: OverflowBox(
        maxWidth: double.infinity, maxHeight: double.infinity,
        child: AnimatedBuilder(
          animation: _c,
          builder: (_, __) {
            final t = _c.value;
            return Opacity(
              opacity: (1 - t) * 0.5,
              child: Container(
                width: 30 + t * 22, height: 30 + t * 22,
                decoration: BoxDecoration(shape: BoxShape.circle,
                    border: Border.all(color: widget.color.withValues(alpha: 0.6), width: 2)),
              ),
            );
          },
        ),
      ))),
      widget.child,
    ]);
  }
}

/// Resolves an employee/photo value that may be a base64 `data:` URI (as the API
/// sends) OR a plain http URL into an [ImageProvider]. Returns null when absent
/// or unparseable, so callers can fall back to initials. `NetworkImage` cannot
/// render `data:` URIs — this is the correct path for API photos.
ImageProvider? avatarImage(String? photo) {
  if (photo == null || photo.isEmpty) return null;
  if (photo.startsWith('data:image')) {
    try {
      return MemoryImage(base64Decode(photo.split(',').last));
    } catch (_) {
      return null;
    }
  }
  if (photo.startsWith('http')) return NetworkImage(photo);
  return null;
}

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
          tooltip: tr('الإشعارات', 'Notifications'),
          onPressed: () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => const NotificationsScreen())),
        ),
        // الشارة فوق الأيقونة — IgnorePointer حتى لا تبتلع الضغطة (كانت تمنع الفتح)
        if (unread > 0)
          Positioned(
            top: 8, right: 6,
            child: IgnorePointer(
              child: Container(
                padding: const EdgeInsets.all(4),
                constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                decoration: const BoxDecoration(color: Color(0xFFE5484D), shape: BoxShape.circle),
                child: Text(unread > 99 ? '99+' : '$unread',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
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
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          // The value scales down instead of overflowing when it's large.
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text('$value',
                style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.w900, height: 1)),
          ),
          const SizedBox(height: 2),
          // Labels like "بالموقع الآن" must wrap/ellipsis, never spill out.
          Text(label,
              textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10.5, height: 1.15, fontWeight: FontWeight.w600, color: Colors.grey.shade700)),
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

/// A subtle, professional geometric pattern for coloured header surfaces —
/// faint diagonal hairlines with a sparse dot grid. Draw it behind content in
/// a Stack/CustomPaint so branded panels read as designed, not flat.
class BrandPattern extends CustomPainter {
  const BrandPattern({this.color = Colors.white, this.opacity = 0.06, this.gap = 26});
  final Color color;
  final double opacity;
  final double gap;

  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..color = color.withValues(alpha: opacity)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    // diagonal hairlines (top-right → bottom-left, RTL-friendly)
    for (double x = -size.height; x < size.width; x += gap) {
      canvas.drawLine(Offset(x, 0), Offset(x + size.height, size.height), line);
    }
    // sparse dot grid on the crossings
    final dot = Paint()..color = color.withValues(alpha: opacity * 1.6);
    for (double y = gap / 2; y < size.height; y += gap) {
      for (double x = gap / 2; x < size.width; x += gap) {
        canvas.drawCircle(Offset(x, y), 1.1, dot);
      }
    }
  }

  @override
  bool shouldRepaint(BrandPattern old) =>
      old.color != color || old.opacity != opacity || old.gap != gap;
}

/// The signed-in person's own photo (served by /me/photo against the app
/// token), falling back to their initial when there is no picture.
class MeAvatar extends StatelessWidget {
  const MeAvatar({super.key, required this.name, this.radius = 28, this.fallbackColor = const Color(0xFF0E3A5F)});
  final String name;
  final double radius;
  final Color fallbackColor;

  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return FutureBuilder<String?>(
      future: api.token,
      builder: (_, snap) {
        final initial = name.trim().isNotEmpty ? name.trim().characters.first : '?';
        Widget fallback() => CircleAvatar(
              radius: radius, backgroundColor: Colors.white,
              child: Text(initial, style: TextStyle(color: fallbackColor, fontSize: radius * 0.85, fontWeight: FontWeight.w900)),
            );
        if (!snap.hasData) return fallback();
        return CircleAvatar(
          radius: radius, backgroundColor: Colors.white,
          child: ClipOval(
            child: Image.network(
              '${api.baseUrl}/me/photo',
              width: radius * 2, height: radius * 2, fit: BoxFit.cover,
              headers: {'Authorization': 'Bearer ${snap.data}'},
              errorBuilder: (_, __, ___) => fallback(),
              loadingBuilder: (c, child, p) => p == null ? child : fallback(),
            ),
          ),
        );
      },
    );
  }
}
