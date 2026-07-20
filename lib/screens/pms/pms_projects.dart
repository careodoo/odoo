import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;
import 'pms_section.dart';
import 'pms_tasks.dart';

/// Projects the user may see (Odoo record rules decide), with real progress.
class PmsProjectsScreen extends StatefulWidget {
  const PmsProjectsScreen({super.key});
  @override
  State<PmsProjectsScreen> createState() => _PmsProjectsScreenState();
}

class _PmsProjectsScreenState extends State<PmsProjectsScreen> {
  late Future<List<dynamic>> _f;
  final _search = TextEditingController();
  Timer? _deb;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _deb?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.pmsProjects(q: _q));

  void _onSearch(String v) {
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 400), () {
      if (!mounted) return;
      _q = v.trim();
      _reload();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(tr('المشاريع', 'Projects')),
      ),
      body: Column(children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: TextField(
            controller: _search,
            onChanged: _onSearch,
            decoration: InputDecoration(
              hintText: tr('ابحث باسم المشروع أو العميل…', 'Search project or client…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              filled: true, fillColor: Pms.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => _reload(),
            child: FutureBuilder<List<dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final rows = snap.data!;
                if (rows.isEmpty) {
                  return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90),
                      child: Center(child: Text(tr('لا مشاريع', 'No projects'),
                          style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700))))]);
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 20),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 9),
                  itemBuilder: (_, i) => _card(rows[i] as Map),
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  Widget _card(Map p) {
    final pct = (numOf(p['progress'], 0)).toDouble();
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => PmsProjectDetail(projectId: p['id'] as int, name: '${p['name']}'))),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: Pms.violet.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                  child: const Icon(Icons.account_tree_rounded, color: Pms.violet, size: 19)),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Pms.ink, height: 1.25)),
                if (p['partner'] != null)
                  Text('${(p['partner'] as Map)['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Pms.slate, fontSize: 11.5)),
              ])),
              Text('${pct.toStringAsFixed(0)}%',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15,
                      color: pct >= 80 ? Pms.green : (pct >= 40 ? Pms.amber : Pms.violet))),
            ]),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: (pct / 100).clamp(0, 1), minHeight: 6,
                backgroundColor: Pms.bg,
                valueColor: AlwaysStoppedAnimation(pct >= 80 ? Pms.green : (pct >= 40 ? Pms.amber : Pms.violet)),
              ),
            ),
            const SizedBox(height: 8),
            Row(children: [
              _chip(Icons.checklist_rounded, tr('${p['tasks']} مهمة', '${p['tasks']} tasks'), Pms.slate),
              const SizedBox(width: 6),
              _chip(Icons.pending_actions_rounded, tr('${p['open']} مفتوحة', '${p['open']} open'), Pms.amber),
              const SizedBox(width: 6),
              _chip(Icons.check_circle_rounded, tr('${p['done']} منجزة', '${p['done']} done'), Pms.green),
            ]),
            if (p['manager'] != null) Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(children: [
                const Icon(Icons.person_rounded, size: 14, color: Pms.slate),
                const SizedBox(width: 5),
                Text('${(p['manager'] as Map)['name']}', style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _chip(IconData i, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(i, size: 12, color: c),
          const SizedBox(width: 4),
          Text(t, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800)),
        ]),
      );
}

/// Project detail: header + progress + its stages, each opening its tasks.
class PmsProjectDetail extends StatefulWidget {
  const PmsProjectDetail({super.key, required this.projectId, required this.name});
  final int projectId;
  final String name;
  @override
  State<PmsProjectDetail> createState() => _PmsProjectDetailState();
}

class _PmsProjectDetailState extends State<PmsProjectDetail> {
  late Future<Map<String, dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.pmsProject(widget.projectId));

  Future<Map<String, dynamic>>? _sectionsF;

  Widget _sections() {
    _sectionsF ??= context.read<AuthProvider>().api.pmsSections(widget.projectId);
    return FutureBuilder<Map<String, dynamic>>(
      future: _sectionsF,
      builder: (_, snap) {
        final list = (snap.data?['sections'] as List?) ?? const [];
        if (list.isEmpty) return const SizedBox.shrink();
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('إدارة المشروع', 'Manage project'),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15)),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 0.86,
            children: [
              for (final x in list)
                Builder(builder: (ctx) {
                  final code = '${(x as Map)['code']}';
                  final c = kPmsSectionColors[code] ?? Pms.violet;
                  return InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () => Navigator.push(ctx, MaterialPageRoute(
                        builder: (_) => PmsSectionScreen(
                            projectId: widget.projectId, code: code, label: '${x['label']}'))),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: c.withValues(alpha: 0.2)),
                      ),
                      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Container(
                          width: 32, height: 32, alignment: Alignment.center,
                          decoration: BoxDecoration(
                              color: c.withValues(alpha: 0.11), borderRadius: BorderRadius.circular(10)),
                          child: Icon(kPmsSectionIcons[code] ?? Icons.folder_rounded, size: 16, color: c),
                        ),
                        const SizedBox(height: 5),
                        Text('${x['label']}',
                            maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, color: c, height: 1.2)),
                      ]),
                    ),
                  );
                }),
            ],
          ),
        ]);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.name, overflow: TextOverflow.ellipsis),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(40),
                  child: Center(child: Text('${snap.error}', textAlign: TextAlign.center)))]);
            }
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final d = snap.data!;
            final pct = (numOf(d['progress'], 0)).toDouble();
            final stages = (d['stages'] as List?) ?? [];
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.black12)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(tr('نسبة الإنجاز', 'Progress'),
                        style: const TextStyle(fontWeight: FontWeight.w800, color: Pms.ink))),
                    Text('${pct.toStringAsFixed(1)}%',
                        style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18,
                            color: pct >= 80 ? Pms.green : (pct >= 40 ? Pms.amber : Pms.violet))),
                  ]),
                  const SizedBox(height: 8),
                  ClipRRect(borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(value: (pct / 100).clamp(0, 1), minHeight: 8,
                        backgroundColor: Pms.bg,
                        valueColor: AlwaysStoppedAnimation(pct >= 80 ? Pms.green : (pct >= 40 ? Pms.amber : Pms.violet)))),
                  const SizedBox(height: 12),
                  Row(children: [
                    _stat('${d['tasks']}', tr('مهمة', 'tasks'), Pms.slate),
                    _stat('${d['open']}', tr('مفتوحة', 'open'), Pms.amber),
                    _stat('${d['done']}', tr('منجزة', 'done'), Pms.green),
                  ]),
                  const Divider(height: 22),
                  if (d['partner'] != null) _kv(Icons.business_rounded, tr('العميل', 'Client'), '${(d['partner'] as Map)['name']}'),
                  if (d['manager'] != null) _kv(Icons.person_rounded, tr('مدير المشروع', 'Manager'), '${(d['manager'] as Map)['name']}'),
                  if (d['date_start'] != null) _kv(Icons.play_arrow_rounded, tr('البداية', 'Start'), '${d['date_start']}'),
                  if (d['date_end'] != null) _kv(Icons.flag_rounded, tr('النهاية', 'End'), '${d['date_end']}'),
                ]),
              ),
              const SizedBox(height: 14),
              // Everything the portal exposes for a project — materials, team,
              // fuel, compliance… — reachable from the project itself.
              _sections(),
              const SizedBox(height: 14),
              Row(children: [
                Text(tr('المراحل', 'Stages'), style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15)),
                const Spacer(),
                TextButton.icon(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => PmsTasksScreen(filter: '', title: widget.name, projectId: widget.projectId))),
                  icon: const Icon(Icons.list_rounded, size: 16),
                  label: Text(tr('كل المهام', 'All tasks')),
                ),
              ]),
              const SizedBox(height: 4),
              for (final s in stages) _stageRow(s as Map),
              if (stages.isEmpty) Padding(padding: const EdgeInsets.all(20),
                  child: Center(child: Text(tr('لا مهام في هذا المشروع', 'No tasks in this project'),
                      style: const TextStyle(color: Pms.slate)))),
            ]);
          },
        ),
      ),
    );
  }

  Widget _stageRow(Map s) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(13),
          child: InkWell(
            borderRadius: BorderRadius.circular(13),
            onTap: () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => PmsTasksScreen(filter: '', title: '${s['name']}',
                    projectId: widget.projectId, stageId: s['id'] as int))),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.black12)),
              child: Row(children: [
                Container(width: 9, height: 9,
                    decoration: BoxDecoration(shape: BoxShape.circle,
                        color: s['fold'] == true ? Pms.green : Pms.violet)),
                const SizedBox(width: 10),
                Expanded(child: Text('${s['name']}',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: Pms.ink))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: Pms.violet.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
                  child: Text('${s['count']}',
                      style: const TextStyle(color: Pms.violet, fontWeight: FontWeight.w900, fontSize: 12)),
                ),
                const Icon(Icons.chevron_left_rounded, color: Pms.slate),
              ]),
            ),
          ),
        ),
      );

  Widget _stat(String v, String l, Color c) => Expanded(
        child: Column(children: [
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Pms.slate)),
        ]),
      );

  Widget _kv(IconData i, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(i, size: 16, color: Pms.slate),
          const SizedBox(width: 8),
          SizedBox(width: 92, child: Text(k, style: const TextStyle(color: Pms.slate, fontSize: 12))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Pms.ink))),
        ]),
      );
}
