import 'package:flutter/material.dart';
import 'i18n.dart';

/// Shared furniture for the client's service pages (security, cleaning,
/// landscaping, facade). They all have the same shape — an identity band with
/// the numbers that matter, a rail of record kinds, and long lists — so they
/// share the parts rather than each inventing them.

const kServiceNavy = Color(0xFF0E3A5F);

/// The service identity band: what this service is, and its live numbers.
class ServiceHero extends StatelessWidget {
  const ServiceHero({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.stats,
    this.onStatTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;

  /// (label, value, optional accent) — rendered in order.
  final List<(String, String, Color?)> stats;
  final void Function(int index)? onStatTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color, Color.lerp(color, Colors.black, 0.35)!],
          begin: Alignment.topRight, end: Alignment.bottomLeft,
        ),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 5))],
      ),
      child: Column(children: [
        Row(children: [
          Container(
            width: 42, height: 42, alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(13),
              border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
            ),
            child: Icon(icon, color: Colors.white, size: 21),
          ),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 16.5, fontWeight: FontWeight.w900)),
            Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 10.5, fontWeight: FontWeight.w600)),
          ])),
        ]),
        if (stats.isNotEmpty) ...[
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (var i = 0; i < stats.length; i++)
              InkWell(
                borderRadius: BorderRadius.circular(11),
                onTap: onStatTap == null ? null : () => onStatTap!(i),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                    color: (stats[i].$3 ?? Colors.white).withValues(alpha: stats[i].$3 != null ? 0.9 : 0.14),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(stats[i].$2,
                        style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w900)),
                    const SizedBox(width: 5),
                    Text(stats[i].$1,
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.85),
                            fontSize: 9.5, fontWeight: FontWeight.w700)),
                  ]),
                ),
              ),
          ]),
        ],
      ]),
    );
  }
}

/// A rail of record kinds, each showing how many records it holds so you can
/// see where the work is before opening anything.
class ServiceTabs extends StatelessWidget {
  const ServiceTabs({
    super.key,
    required this.kinds,
    required this.current,
    required this.onSelect,
    required this.color,
    this.counts = const {},
  });

  /// (code, arabic label, english label, icon) — the tab strip is shared by
  /// four service consoles, so carrying both languages here translates all of
  /// them at once.
  final List<(String, String, String, IconData)> kinds;
  final String current;
  final ValueChanged<String> onSelect;
  final Color color;
  final Map<String, int> counts;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: kinds.length,
        separatorBuilder: (_, __) => const SizedBox(width: 7),
        itemBuilder: (_, i) {
          final k = kinds[i];
          final on = k.$1 == current;
          final n = counts[k.$1];
          return InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: () => onSelect(k.$1),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 11),
              decoration: BoxDecoration(
                color: on ? color : color.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(11),
                border: Border.all(color: on ? color : color.withValues(alpha: 0.18)),
              ),
              child: Row(children: [
                Icon(k.$4, size: 14, color: on ? Colors.white : color),
                const SizedBox(width: 6),
                Text(tr(k.$2, k.$3),
                    style: TextStyle(
                        fontSize: 11.5, fontWeight: FontWeight.w800,
                        color: on ? Colors.white : color)),
                if (n != null && n > 0) ...[
                  const SizedBox(width: 5),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: on ? Colors.white.withValues(alpha: 0.25) : color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text('$n',
                        style: TextStyle(
                            fontSize: 8.5, fontWeight: FontWeight.w900,
                            color: on ? Colors.white : color)),
                  ),
                ],
              ]),
            ),
          );
        },
      ),
    );
  }
}

/// A list that shows a first page and reveals the rest on demand. Long lists
/// used to render every row at once; now the count is stated up front and
/// "المزيد" is an explicit, visible action rather than an endless scroll.
class MoreList extends StatefulWidget {
  const MoreList({
    super.key,
    required this.items,
    required this.itemBuilder,
    this.pageSize = 8,
    this.color = kServiceNavy,
    this.emptyText,
    this.header,
  });

  final List items;
  final Widget Function(BuildContext, dynamic, int) itemBuilder;
  final int pageSize;
  final Color color;
  final String? emptyText;

  /// Optional line above the list; the total count is appended to it.
  final String? header;

  @override
  State<MoreList> createState() => _MoreListState();
}

class _MoreListState extends State<MoreList> {
  late int _shown = widget.pageSize;

  @override
  void didUpdateWidget(MoreList old) {
    super.didUpdateWidget(old);
    // A new filter/kind means a new list — start from the first page again,
    // otherwise a short list would inherit a long list's expansion.
    if (!identical(old.items, widget.items)) _shown = widget.pageSize;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 42),
        child: Center(child: Column(children: [
          Icon(Icons.inbox_rounded, size: 36, color: Colors.grey.shade300),
          const SizedBox(height: 8),
          Text(widget.emptyText ?? tr('لا سجلات.', 'Nothing here.'),
              style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5)),
        ])),
      );
    }
    final n = widget.items.length;
    final shown = _shown.clamp(0, n);
    final rest = n - shown;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (widget.header != null)
        Padding(
          padding: const EdgeInsets.only(bottom: 7, right: 2),
          child: Row(children: [
            Text(widget.header!,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
            const SizedBox(width: 6),
            Text(
                // Say what is on screen vs. what exists — a cut list must never
                // read as the whole set.
                rest > 0
                    ? tr('عرض $shown من $n', 'showing $shown of $n')
                    : '$n',
                style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: Colors.grey.shade500)),
          ]),
        ),
      for (var i = 0; i < shown; i++) widget.itemBuilder(context, widget.items[i], i),
      if (rest > 0)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: widget.color,
                side: BorderSide(color: widget.color.withValues(alpha: 0.4)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 11),
              ),
              icon: const Icon(Icons.expand_more_rounded, size: 18),
              label: Text(
                  tr('عرض المزيد ($rest)', 'Show more ($rest)'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
              onPressed: () => setState(() => _shown += widget.pageSize * 2),
            ),
          ),
        ),
      if (rest == 0 && n > widget.pageSize)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Center(child: TextButton.icon(
            icon: const Icon(Icons.expand_less_rounded, size: 16),
            label: Text(tr('طيّ القائمة', 'Collapse'), style: const TextStyle(fontSize: 11.5)),
            onPressed: () => setState(() => _shown = widget.pageSize),
          )),
        ),
    ]);
  }
}
