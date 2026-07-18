import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Edit a record's name in every active language (English is the base, the rest
/// are its translations). Used from the manage screen for facilities, buildings,
/// floors, locations, assets and teams — so any fixed name can be multilingual.
class TranslateDialog extends StatefulWidget {
  const TranslateDialog({super.key, required this.kind, required this.id, this.currentName});
  final String kind;
  final int id;
  final String? currentName;

  static Future<bool?> open(BuildContext context, {required String kind, required int id, String? currentName}) =>
      showDialog<bool>(context: context, builder: (_) => TranslateDialog(kind: kind, id: id, currentName: currentName));

  @override
  State<TranslateDialog> createState() => _TranslateDialogState();
}

class _TranslateDialogState extends State<TranslateDialog> {
  List<dynamic>? _langs;
  final Map<String, TextEditingController> _ctrls = {};
  bool _loading = true, _saving = false;
  String? _error;

  static const _accent = Color(0xFF6366F1);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) { c.dispose(); }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final langs = await api.i18nLanguages();
      final cur = await api.i18nGet(widget.kind, widget.id);
      final vals = (cur['values'] as Map?) ?? const {};
      if (!mounted) return;
      setState(() {
        _langs = langs;
        for (final l in langs) {
          final code = '${l['code']}';
          _ctrls[code] = TextEditingController(text: '${vals[code] ?? ''}');
        }
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() { _loading = false; _error = '$e'; });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final values = {for (final e in _ctrls.entries) e.key: e.value.text.trim()};
    try {
      await context.read<AuthProvider>().api.i18nSet(widget.kind, widget.id, values);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('حُفظت الترجمات', 'Translations saved')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) { setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'))); }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 440, maxHeight: 560),
        padding: const EdgeInsets.all(18),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            const Icon(Icons.translate_rounded, color: _accent),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('الترجمات', 'Translations'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Color(0xFF0E3A5F)))),
            IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.pop(context)),
          ]),
          if (widget.currentName != null)
            Align(alignment: Alignment.centerRight, child: Text(widget.currentName!,
                style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600))),
          const SizedBox(height: 8),
          Expanded(child: _loading
              ? const Center(child: CircularProgressIndicator(color: _accent))
              : _error != null
                  ? Center(child: Text(_error!, style: const TextStyle(color: Colors.grey)))
                  : ListView(children: [
                      Text(tr('الإنجليزية هي الأساس، والبقية ترجماتها.', 'English is the base; the rest are its translations.'),
                          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500)),
                      const SizedBox(height: 10),
                      for (final l in _langs!) _field(l as Map),
                    ])),
          const SizedBox(height: 10),
          SizedBox(width: double.infinity, height: 48, child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: _accent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
            onPressed: (_loading || _saving) ? null : _save,
            icon: _saving ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.save_rounded),
            label: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          )),
        ]),
      ),
    );
  }

  Widget _field(Map l) {
    final code = '${l['code']}';
    final isBase = code == 'en_US';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: _ctrls[code],
        decoration: InputDecoration(
          labelText: '${l['name']}${isBase ? ' · ${tr('الأساس', 'base')}' : ''}',
          prefixIcon: Icon(isBase ? Icons.star_rounded : Icons.translate_rounded,
              size: 18, color: isBase ? const Color(0xFFF59E0B) : _accent),
          filled: true, fillColor: isBase ? const Color(0xFFFFF7E6) : const Color(0xFFF4F6F8),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          isDense: true,
        ),
      ),
    );
  }
}
