import 'package:flutter/material.dart';
import '../core/i18n.dart';

/// One selectable option. [label] is what's shown; [search] is extra text the
/// filter also matches (e.g. the other-language name, a code, a job title) so a
/// search succeeds in whatever language/term the user types.
class PickOption {
  const PickOption({required this.value, required this.label, this.sublabel, this.search, this.icon, this.color});
  final Object? value;
  final String label;
  final String? sublabel;
  final String? search;
  final IconData? icon;
  final Color? color;
  String get _hay => '$label ${sublabel ?? ''} ${search ?? ''}'.toLowerCase();
}

/// A searchable replacement for a flat DropdownButton: opens a sheet with a
/// search box that filters across every language/term attached to each option.
/// Returns the chosen option's [value], or null if dismissed.
class SearchablePicker {
  static Future<Object?> open(BuildContext context, {
    required List<PickOption> options,
    String? title,
    Object? selected,
    bool allowClear = false,
    Color accent = const Color(0xFF0E3A5F),
  }) =>
      showModalBottomSheet<Object?>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => _PickerSheet(options: options, title: title, selected: selected, allowClear: allowClear, accent: accent),
      );
}

class _PickerSheet extends StatefulWidget {
  const _PickerSheet({required this.options, this.title, this.selected, required this.allowClear, required this.accent});
  final List<PickOption> options;
  final String? title;
  final Object? selected;
  final bool allowClear;
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
        : widget.options.where((o) => o._hay.contains(_q.toLowerCase())).toList();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, minChildSize: 0.4, maxChildSize: 0.95,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 12, 10, 12),
            decoration: BoxDecoration(gradient: LinearGradient(
                colors: [widget.accent, Color.lerp(widget.accent, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Row(children: [
              Expanded(child: Text(widget.title ?? tr('اختر', 'Select'),
                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
              if (widget.allowClear)
                TextButton(onPressed: () => Navigator.pop(context, _cleared),
                    child: Text(tr('مسح', 'Clear'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
              IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
            child: TextField(
              autofocus: true,
              onChanged: (v) => setState(() => _q = v),
              decoration: InputDecoration(
                hintText: tr('ابحث بأي لغة…', 'Search in any language…'),
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                isDense: true, filled: true, fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              ),
            ),
          ),
          Expanded(child: filtered.isEmpty
              ? Center(child: Text(tr('لا نتائج', 'No matches'), style: TextStyle(color: Colors.grey.shade500)))
              : ListView.builder(
                  controller: sc, padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
                  itemCount: filtered.length,
                  itemBuilder: (_, i) {
                    final o = filtered[i];
                    final on = o.value == widget.selected;
                    return Container(
                      margin: const EdgeInsets.only(bottom: 7),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: on ? widget.accent : Colors.transparent, width: 1.5)),
                      child: ListTile(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        leading: o.icon == null ? null : Container(
                          width: 38, height: 38, alignment: Alignment.center,
                          decoration: BoxDecoration(color: (o.color ?? widget.accent).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                          child: Icon(o.icon, color: o.color ?? widget.accent, size: 20)),
                        title: Text(o.label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
                        subtitle: o.sublabel == null ? null : Text(o.sublabel!, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
                        trailing: on ? Icon(Icons.check_circle_rounded, color: widget.accent) : const Icon(Icons.chevron_left_rounded, color: Colors.grey),
                        onTap: () => Navigator.pop(context, o.value),
                      ),
                    );
                  },
                )),
        ]),
      ),
    );
  }
}

/// Sentinel returned when the user taps "Clear".
const Object _cleared = Object();
bool isCleared(Object? v) => identical(v, _cleared);

/// A form-field-styled button that opens [SearchablePicker] and shows the
/// current selection. Drop-in replacement for a labelled dropdown.
class SearchableField extends StatelessWidget {
  const SearchableField({
    super.key, required this.label, required this.options, required this.value,
    required this.onChanged, this.icon = Icons.search_rounded, this.accent = const Color(0xFF0E3A5F),
    this.allowClear = true,
  });
  final String label;
  final List<PickOption> options;
  final Object? value;
  final ValueChanged<Object?> onChanged;
  final IconData icon;
  final Color accent;
  final bool allowClear;

  @override
  Widget build(BuildContext context) {
    final sel = value == null ? null : options.where((o) => o.value == value);
    final selLabel = (sel != null && sel.isNotEmpty) ? sel.first.label : null;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () async {
        final r = await SearchablePicker.open(context, options: options, title: label, selected: value, allowClear: allowClear, accent: accent);
        if (r == null) return;
        onChanged(isCleared(r) ? null : r);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label, prefixIcon: Icon(icon, size: 19),
          filled: true, fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        ),
        child: Row(children: [
          Expanded(child: Text(selLabel ?? tr('اختر…', 'Select…'),
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 13.5, fontWeight: selLabel != null ? FontWeight.w800 : FontWeight.w500,
                  color: selLabel != null ? const Color(0xFF0E3A5F) : Colors.grey.shade500))),
          const Icon(Icons.expand_more_rounded, color: Colors.grey, size: 20),
        ]),
      ),
    );
  }
}
