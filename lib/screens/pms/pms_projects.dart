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
  String _sort = 'name'; // name | progress | at_risk | open

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
                final rows = snap.data!.cast<Map>().toList();
                if (rows.isEmpty) {
                  return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90),
                      child: Center(child: Text(tr('لا مشاريع', 'No projects'),
                          style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700))))]);
                }
                final n = rows.length;
                final avg = n > 0 ? rows.map((p) => numOf(p['progress'], 0)).reduce((a, b) => a + b) / n : 0.0;
                final atRisk = rows.where((p) => p['health'] == 'at_risk').length;
                final totalOpen = rows.map((p) => numOf(p['open'], 0)).fold<num>(0, (a, b) => a + b);
                rows.sort((a, b) {
                  switch (_sort) {
                    case 'progress': return numOf(b['progress'], 0).compareTo(numOf(a['progress'], 0));
                    case 'open': return numOf(b['open'], 0).compareTo(numOf(a['open'], 0));
                    case 'at_risk': return numOf(b['overdue'], 0).compareTo(numOf(a['overdue'], 0));
                    default: return '${a['name']}'.compareTo('${b['name']}');
                  }
                });
                return ListView(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 20),
                  children: [
                    _summaryBand(n, avg.toDouble(), atRisk, totalOpen.toInt()),
                    const SizedBox(height: 12),
                    _sortRow(),
                    const SizedBox(height: 10),
                    for (final p in rows) Padding(
                      padding: const EdgeInsets.only(bottom: 9),
                      child: _card(p),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  static const _healthColors = {
    'on_track': Pms.green, 'at_risk': Pms.red, 'done': Color(0xFF0891B2),
  };
  String _healthLabel(String h) => {
        'on_track': tr('على المسار', 'On track'),
        'at_risk': tr('متعثّر', 'At risk'),
        'done': tr('مكتمل', 'Completed'),
      }[h] ?? h;

  Widget _summaryBand(int n, double avg, int atRisk, int open) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Pms.violet, Pms.deep],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(color: Pms.violet.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 5))],
        ),
        child: Row(children: [
          _sumCell('$n', tr('مشروع', 'Projects')),
          _sumDivider(),
          _sumCell('${avg.toStringAsFixed(0)}%', tr('متوسط الإنجاز', 'Avg progress')),
          _sumDivider(),
          _sumCell('$open', tr('مهام مفتوحة', 'Open tasks')),
          _sumDivider(),
          _sumCell('$atRisk', tr('متعثّرة', 'At risk'), warn: atRisk > 0),
        ]),
      );

  Widget _sumCell(String v, String l, {bool warn = false}) => Expanded(
        child: Column(children: [
          Text(v, style: TextStyle(color: warn ? const Color(0xFFFFD1D1) : Colors.white,
              fontWeight: FontWeight.w900, fontSize: 18)),
          const SizedBox(height: 2),
          Text(l, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 9.5, fontWeight: FontWeight.w700, height: 1.15)),
        ]),
      );

  Widget _sumDivider() => Container(width: 1, height: 30, color: Colors.white24);

  Widget _sortRow() {
    const opts = [
      ('name', 'الاسم', 'Name'), ('progress', 'الأعلى إنجازًا', 'Progress'),
      ('open', 'الأكثر مهامًا', 'Most tasks'), ('at_risk', 'المتعثّرة', 'At risk'),
    ];
    return SizedBox(
      height: 32,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        for (final o in opts) Padding(
          padding: const EdgeInsets.only(left: 6),
          child: ChoiceChip(
            label: Text(tr(o.$2, o.$3), style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
            selected: _sort == o.$1,
            selectedColor: Pms.violet,
            labelStyle: TextStyle(color: _sort == o.$1 ? Colors.white : Pms.ink),
            onSelected: (_) => setState(() => _sort = o.$1),
          ),
        ),
      ]),
    );
  }

  Widget _card(Map p) {
    final pct = (numOf(p['progress'], 0)).toDouble();
    final health = '${p['health'] ?? 'on_track'}';
    final hc = _healthColors[health] ?? Pms.slate;
    final barC = pct >= 80 ? Pms.green : (pct >= 40 ? Pms.amber : Pms.violet);
    final overdue = numOf(p['overdue'], 0).toInt();
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => PmsProjectDetail(projectId: p['id'] as int, name: '${p['name']}'))),
        child: Container(
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Container(width: 5, color: hc),
            Expanded(child: Padding(
              padding: const EdgeInsets.fromLTRB(13, 13, 13, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Pms.ink, height: 1.25))),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: hc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                    child: Text(_healthLabel(health),
                        style: TextStyle(color: hc, fontWeight: FontWeight.w800, fontSize: 9.5)),
                  ),
                ]),
                if (p['partner'] != null) Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${(p['partner'] as Map)['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Pms.slate, fontSize: 11.5)),
                ),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(value: (pct / 100).clamp(0, 1), minHeight: 7,
                        backgroundColor: Pms.bg, valueColor: AlwaysStoppedAnimation(barC)),
                  )),
                  const SizedBox(width: 8),
                  Text('${pct.toStringAsFixed(0)}%',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: barC)),
                ]),
                const SizedBox(height: 9),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  _chip(Icons.pending_actions_rounded, '${p['open']} ${tr('مفتوحة', 'open')}', Pms.amber),
                  _chip(Icons.check_circle_rounded, '${p['done']} ${tr('منجزة', 'done')}', Pms.green),
                  if (overdue > 0) _chip(Icons.local_fire_department_rounded, '$overdue ${tr('متأخرة', 'overdue')}', Pms.red),
                  if (numOf(p['team'], 0) > 0) _chip(Icons.groups_rounded, '${p['team']} ${tr('عامل', 'staff')}', const Color(0xFF0D9488)),
                ]),
                if (p['manager'] != null) Padding(
                  padding: const EdgeInsets.only(top: 9),
                  child: Row(children: [
                    const Icon(Icons.person_rounded, size: 14, color: Pms.slate),
                    const SizedBox(width: 5),
                    Expanded(child: Text('${(p['manager'] as Map)['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11.5, color: Pms.slate))),
                    if (p['date_end'] != null) ...[
                      const Icon(Icons.flag_rounded, size: 13, color: Pms.slate),
                      const SizedBox(width: 3),
                      Text('${p['date_end']}', style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
                    ],
                  ]),
                ),
              ]),
            )),
          ])),
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
          Row(children: [
            Text(tr('إدارة المشروع', 'Manage project'),
                style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15)),
            const Spacer(),
            Icon(Icons.touch_app_rounded, size: 13, color: Pms.slate),
            const SizedBox(width: 3),
            Text(tr('اضغط مطوّلاً للتفويض', 'Long-press to delegate'),
                style: const TextStyle(fontSize: 10, color: Pms.slate, fontWeight: FontWeight.w600)),
          ]),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.02,
            children: [
              for (final x in list)
                Builder(builder: (ctx) {
                  final code = '${(x as Map)['code']}';
                  final c = kPmsSectionColors[code] ?? Pms.violet;
                  return Material(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => Navigator.push(ctx, MaterialPageRoute(
                          builder: (_) => PmsSectionScreen(
                              projectId: widget.projectId, code: code, label: '${x['label']}'))),
                      onLongPress: () => _delegateSheet(code, '${x['label']}'),
                      child: Container(
                        padding: const EdgeInsets.all(11),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: c.withValues(alpha: 0.18)),
                          gradient: LinearGradient(colors: [c.withValues(alpha: 0.10), Colors.white],
                              begin: Alignment.topRight, end: Alignment.bottomLeft),
                          boxShadow: [BoxShadow(color: c.withValues(alpha: 0.10),
                              blurRadius: 8, offset: const Offset(0, 3))],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              width: 40, height: 40, alignment: Alignment.center,
                              decoration: BoxDecoration(
                                  gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.22)!],
                                      begin: Alignment.topLeft, end: Alignment.bottomRight),
                                  borderRadius: BorderRadius.circular(12),
                                  boxShadow: [BoxShadow(color: c.withValues(alpha: 0.35),
                                      blurRadius: 6, offset: const Offset(0, 3))]),
                              child: Icon(kPmsSectionIcons[code] ?? Icons.folder_rounded, size: 21, color: Colors.white),
                            ),
                            Text('${x['label']}',
                                maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                                    color: Pms.ink, height: 1.2)),
                          ],
                        ),
                      ),
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
              _projectHero(d, pct),
              const SizedBox(height: 16),
              // Everything about the project as clickable headline counts —
              // workers, vehicles, correspondence, custody, materials, cash.
              if (((d['stats'] as List?) ?? const []).isNotEmpty) ...[
                _miniHead(tr('إحصائيات المشروع', 'Project statistics'), Icons.insights_rounded, Pms.violet),
                const SizedBox(height: 8),
                GridView.count(
                  crossAxisCount: 3, shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 9, crossAxisSpacing: 9, childAspectRatio: 0.95,
                  children: [for (final s in (d['stats'] as List)) _statCard(s as Map)],
                ),
                const SizedBox(height: 16),
              ],
              // Everything the portal exposes for a project — materials, team,
              // fuel, compliance… — reachable from the project itself.
              _sections(),
              if (((d['team_preview'] as List?) ?? const []).isNotEmpty) ...[
                const SizedBox(height: 16),
                _teamPreview((d['team_preview'] as List).cast<Map>()),
              ],
              if (((d['upcoming'] as List?) ?? const []).isNotEmpty) ...[
                const SizedBox(height: 16),
                _miniHead(tr('مواعيد قادمة', 'Upcoming deadlines'), Icons.upcoming_rounded, Pms.amber),
                const SizedBox(height: 8),
                for (final t in (d['upcoming'] as List).take(4)) _taskMini(t as Map),
              ],
              if (((d['recent_tasks'] as List?) ?? const []).isNotEmpty) ...[
                const SizedBox(height: 16),
                _miniHead(tr('آخر النشاط', 'Recent activity'), Icons.history_rounded, const Color(0xFF0891B2)),
                const SizedBox(height: 8),
                for (final t in (d['recent_tasks'] as List).take(4)) _taskMini(t as Map),
              ],
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

  Widget _miniHead(String t, IconData ic, Color c) => Row(children: [
        Icon(ic, size: 17, color: c),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15)),
      ]);

  /// A professional project hero — completion ring, task split, and the key
  /// facts (client / manager / dates), all in one organized card.
  Widget _projectHero(Map d, double pct) {
    Widget stat(String v, String l) => Column(mainAxisSize: MainAxisSize.min, children: [
          Text(v, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 10, fontWeight: FontWeight.w700)),
        ]);
    Widget info(IconData ic, String label, String value) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(children: [
            Icon(ic, size: 15, color: Colors.white.withValues(alpha: 0.85)),
            const SizedBox(width: 8),
            Text('$label:', style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 11.5)),
            const SizedBox(width: 6),
            Expanded(child: Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12))),
          ]),
        );
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Pms.violet, Pms.deep, Color(0xFF3B0F73)],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: Pms.violet.withValues(alpha: 0.32), blurRadius: 14, offset: const Offset(0, 6))],
      ),
      child: Column(children: [
        Row(children: [
          SizedBox(
            width: 84, height: 84,
            child: Stack(alignment: Alignment.center, children: [
              SizedBox(width: 84, height: 84, child: CircularProgressIndicator(
                value: (pct / 100).clamp(0, 1), strokeWidth: 8, strokeCap: StrokeCap.round,
                backgroundColor: Colors.white.withValues(alpha: 0.18),
                valueColor: const AlwaysStoppedAnimation(Colors.white))),
              Column(mainAxisSize: MainAxisSize.min, children: [
                Text('${pct.toStringAsFixed(0)}%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19, height: 1)),
                Text(tr('إنجاز', 'done'), style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 9)),
              ]),
            ]),
          ),
          const SizedBox(width: 16),
          Expanded(child: Row(children: [
            Expanded(child: stat('${d['tasks'] ?? 0}', tr('مهمة', 'tasks'))),
            Container(width: 1, height: 30, color: Colors.white24),
            Expanded(child: stat('${d['open'] ?? 0}', tr('مفتوحة', 'open'))),
            Container(width: 1, height: 30, color: Colors.white24),
            Expanded(child: stat('${d['done'] ?? 0}', tr('منجزة', 'done'))),
          ])),
        ]),
        Divider(height: 24, color: Colors.white.withValues(alpha: 0.18)),
        if (d['partner'] != null) info(Icons.business_rounded, tr('العميل', 'Client'), '${(d['partner'] as Map)['name']}'),
        if (d['manager'] != null) info(Icons.person_rounded, tr('مدير المشروع', 'Manager'), '${(d['manager'] as Map)['name']}'),
        if (d['date_start'] != null) info(Icons.play_arrow_rounded, tr('البداية', 'Start'), '${d['date_start']}'),
        if (d['date_end'] != null) info(Icons.flag_rounded, tr('النهاية', 'End'), '${d['date_end']}'),
      ]),
    );
  }

  Widget _teamPreview(List<Map> team) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.groups_rounded, size: 17, color: Color(0xFF0D9488)),
          const SizedBox(width: 7),
          Text(tr('فريق المشروع', 'Project team'),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14.5)),
          const Spacer(),
          TextButton(
            onPressed: () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => PmsSectionScreen(projectId: widget.projectId, code: 'team', label: tr('الفريق', 'Team')))),
            child: Text(tr('الكل', 'All')),
          ),
        ]),
        const SizedBox(height: 6),
        SizedBox(
          height: 78,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: team.length,
            separatorBuilder: (_, __) => const SizedBox(width: 12),
            itemBuilder: (_, i) {
              final e = team[i];
              return SizedBox(
                width: 60,
                child: Column(children: [
                  CircleAvatar(
                    radius: 24, backgroundColor: const Color(0xFF0D9488).withValues(alpha: 0.12),
                    backgroundImage: e['avatar'] != null ? NetworkImage('${e['avatar']}') : null,
                    onBackgroundImageError: (_, __) {},
                    child: e['avatar'] == null
                        ? Text('${e['name'] ?? '?'}'.characters.first,
                            style: const TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.w900))
                        : null,
                  ),
                  const SizedBox(height: 4),
                  Text('${e['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: Pms.ink)),
                ]),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _taskMini(Map t) {
    final overdue = t['overdue'] == true;
    final done = t['done'] == true;
    final c = done ? Pms.green : (overdue ? Pms.red : Pms.violet);
    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () async {
            await Navigator.push(context, MaterialPageRoute(builder: (_) => PmsTaskDetail(taskId: t['id'] as int)));
            _reload();
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 10),
            child: Row(children: [
              Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
              const SizedBox(width: 10),
              Expanded(child: Text('${t['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Pms.ink,
                      decoration: done ? TextDecoration.lineThrough : null))),
              if (t['deadline'] != null) ...[
                const SizedBox(width: 8),
                Icon(Icons.event_rounded, size: 12, color: overdue ? Pms.red : Pms.slate),
                const SizedBox(width: 3),
                Text('${t['deadline']}'.split(' ').first,
                    style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: overdue ? Pms.red : Pms.slate)),
              ],
              if (t['stage'] != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
                  child: Text('${(t['stage'] as Map)['name']}', style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w800)),
                ),
              ],
            ]),
          ),
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

  static const _statIcons = {
    'checklist': Icons.checklist_rounded,
    'pending_actions': Icons.pending_actions_rounded,
    'check_circle': Icons.check_circle_rounded,
    'local_fire_department': Icons.local_fire_department_rounded,
    'groups': Icons.groups_rounded,
    'fmd_good': Icons.fmd_good_rounded,
    'verified_user': Icons.verified_user_rounded,
    'directions_car': Icons.directions_car_rounded,
    'mail': Icons.mail_rounded,
    'inventory_2': Icons.inventory_2_rounded,
    'inventory': Icons.inventory_rounded,
    'receipt': Icons.receipt_long_rounded,
    'local_shipping': Icons.local_shipping_rounded,
    'description': Icons.description_rounded,
    'timer': Icons.timer_rounded,
    'payments': Icons.payments_rounded,
    'receipt_long': Icons.receipt_long_rounded,
  };
  static const _statColors = {
    '__tasks__': Pms.violet, '__open__': Color(0xFFF59E0B), '__done__': Color(0xFF16A34A),
    '__overdue__': Color(0xFFE11D48), 'team': Color(0xFF2563EB), 'attendance': Color(0xFF0EA5E9),
    'compliance': Color(0xFFE5484D), 'fuel': Color(0xFF0D9488), '__letters__': Color(0xFF9333EA),
    'assets': Color(0xFF0E7490), 'materials': Color(0xFF7C3AED), 'deliveries': Color(0xFF6366F1),
    'supplies': Color(0xFF0EA5E9), 'requests': Color(0xFF8B5CF6), 'timesheet': Color(0xFF7C3AED),
    'petty': Color(0xFFD97706), 'invoices': Color(0xFF9D174D),
  };

  Widget _statCard(Map s) {
    final code = '${s['code']}';
    final c = _statColors[code] ?? Pms.violet;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openStat(code, '${s['label']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: c.withValues(alpha: 0.18)),
              gradient: LinearGradient(colors: [c.withValues(alpha: 0.10), Colors.white],
                  begin: Alignment.topRight, end: Alignment.bottomLeft)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(children: [
                Container(
                  width: 30, height: 30, alignment: Alignment.center,
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(9)),
                  child: Icon(_statIcons['${s['icon']}'] ?? Icons.insights_rounded, size: 17, color: c),
                ),
                const Spacer(),
                Icon(Icons.chevron_left_rounded, size: 16, color: c.withValues(alpha: 0.5)),
              ]),
              Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text('${s['count']}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: c, height: 1)),
                const SizedBox(height: 3),
                Text('${s['label']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 10, color: Pms.ink, height: 1.15)),
              ]),
            ],
          ),
        ),
      ),
    );
  }

  /// Delegate follow-up of a dashboard section to a supervisor (manager only).
  Future<void> _delegateSheet(String code, String label) async {
    final api = context.read<AuthProvider>().api;
    Map<String, dynamic> data;
    try {
      data = await api.pmsDelegations(widget.projectId);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
      return;
    }
    if (!mounted) return;
    final users = ((data['users'] as List?) ?? const []).cast<Map>();
    var current = ((data['delegations'] as List?) ?? const [])
        .cast<Map>()
        .where((d) => d['section_code'] == code)
        .toList();
    int? pick;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) {
        Future<void> refresh() async {
          final d = await api.pmsDelegations(widget.projectId);
          setSheet(() => current = ((d['delegations'] as List?) ?? const [])
              .cast<Map>().where((x) => x['section_code'] == code).toList());
        }
        return Padding(
          padding: EdgeInsets.fromLTRB(18, 14, 18, MediaQuery.of(ctx).viewInsets.bottom + 20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.supervisor_account_rounded, color: Pms.violet),
              const SizedBox(width: 8),
              Expanded(child: Text(tr('تفويض متابعة: $label', 'Delegate: $label'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))),
            ]),
            const SizedBox(height: 6),
            Text(tr('اختر مشرفًا ليتابع هذا القسم نيابةً عنك.',
                'Assign a supervisor to follow up this section for you.'),
                style: const TextStyle(color: Pms.slate, fontSize: 12)),
            const SizedBox(height: 14),
            if (current.isNotEmpty) ...[
              Text(tr('المفوَّضون حاليًا', 'Currently delegated'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Pms.ink)),
              const SizedBox(height: 6),
              for (final d in current)
                Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(color: Pms.violet.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    const Icon(Icons.person_rounded, size: 18, color: Pms.violet),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${d['delegate']}',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5))),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 18, color: Pms.red),
                      onPressed: () async {
                        try {
                          await api.pmsDelegationRevoke(d['id'] as int);
                          await refresh();
                        } catch (_) {}
                      },
                    ),
                  ]),
                ),
              const SizedBox(height: 12),
            ],
            DropdownButtonFormField<int>(
              value: pick, isExpanded: true,
              decoration: InputDecoration(labelText: tr('المشرف', 'Supervisor'),
                  prefixIcon: const Icon(Icons.badge_rounded),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
              items: [for (final u in users) DropdownMenuItem(value: u['id'] as int,
                  child: Text('${u['name']}', overflow: TextOverflow.ellipsis))],
              onChanged: (v) => setSheet(() => pick = v),
            ),
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, height: 48, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.violet,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: pick == null ? null : () async {
                try {
                  await api.pmsDelegate(widget.projectId, {
                    'delegate_id': pick, 'section_code': code, 'section_label': label,
                  });
                  await refresh();
                  setSheet(() => pick = null);
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
                        backgroundColor: Pms.green,
                        content: Text(tr('تم التفويض وإشعار المشرف', 'Delegated and notified'))));
                  }
                } catch (e) {
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
                  }
                }
              },
              icon: const Icon(Icons.check_rounded),
              label: Text(tr('تفويض', 'Delegate'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          ]),
        );
      }),
    );
  }

  static const _taskFilters = {
    '__tasks__': '', '__open__': 'open', '__done__': 'done', '__overdue__': 'overdue',
  };

  void _openStat(String code, String label) {
    if (_taskFilters.containsKey(code)) {
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PmsTasksScreen(
              filter: _taskFilters[code]!, title: label, projectId: widget.projectId)));
    } else if (code == '__letters__') {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('الكتب والمراسلات تُدار من نظام المراسلات',
              'Correspondence is managed in the letters system'))));
    } else {
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PmsSectionScreen(projectId: widget.projectId, code: code, label: label)));
    }
  }
}
