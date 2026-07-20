import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth.dart';
import '../core/i18n.dart';
import 'svc_section_screen.dart';

/// The sections one service is made of, read from the backend registry.
///
/// Nothing here is hard-coded per service: add a section on the server and it
/// appears in this list, in the web portal, and nowhere has to be kept in step.
class SvcSectionsHub extends StatefulWidget {
  const SvcSectionsHub({
    super.key,
    required this.code,
    required this.title,
    this.accent = const Color(0xFF0D9488),
  });

  final String code;
  final String title;
  final Color accent;

  @override
  State<SvcSectionsHub> createState() => _SvcSectionsHubState();
}

class _SvcSectionsHubState extends State<SvcSectionsHub> {
  List<Map> _sections = const [];
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.svcRegistry();
      final svcs = ((d['services'] as List?) ?? const []).cast<Map>();
      final me = svcs.firstWhere((s) => s['code'] == widget.code,
          orElse: () => const {});
      if (mounted) {
        setState(() {
          _sections = ((me['sections'] as List?) ?? const []).cast<Map>();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = '$e'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: widget.accent,
        foregroundColor: Colors.white,
        title: Text('${tr('سجلات', 'Records')} · ${widget.title}',
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      ),
      body: _loading
          ? Center(child: CircularProgressIndicator(color: widget.accent))
          : _sections.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Text(
                        _error ?? tr('لا توجد أقسام لهذه الخدمة',
                                     'No sections for this service'),
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey.shade600)),
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: _sections.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 9),
                  itemBuilder: (_, i) {
                    final s = _sections[i];
                    final canAdd = s['can_add'] == true;
                    return Material(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => Navigator.push(context, MaterialPageRoute(
                            builder: (_) => SvcSectionScreen(
                                  code: widget.code,
                                  sectionKey: '${s['key']}',
                                  title: '${s['label']}',
                                  accent: widget.accent,
                                ))),
                        child: Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: Colors.grey.shade200)),
                          child: Row(children: [
                            Container(
                              width: 40, height: 40, alignment: Alignment.center,
                              decoration: BoxDecoration(
                                  color: widget.accent.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(11)),
                              child: Text('${s['icon'] ?? '•'}',
                                  style: const TextStyle(fontSize: 18)),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${s['label']}',
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w900,
                                          fontSize: 14)),
                                  if (canAdd) ...[
                                    const SizedBox(height: 2),
                                    Text(
                                        '${s['add_label'] ?? tr('يمكنك الإضافة', 'You can add')}',
                                        style: const TextStyle(
                                            fontSize: 11.5,
                                            fontWeight: FontWeight.w700,
                                            color: Color(0xFF16A34A))),
                                  ],
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_left_rounded,
                                color: Colors.grey.shade400),
                          ]),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
