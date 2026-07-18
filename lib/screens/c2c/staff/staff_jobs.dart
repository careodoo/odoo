import 'dart:convert';
import 'package:flutter/material.dart';
import '../../media_viewer_screen.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../../core/auth.dart';
import '../../../core/i18n.dart';
import 'staff_shell.dart';

/// The crew jobs list — filter chips + cards. Each card opens a role-gated
/// detail screen (start / complete / add proof / assign / quality / approve).
class StaffJobsScreen extends StatefulWidget {
  const StaffJobsScreen({super.key, required this.me, this.embedded = false, this.defaultFilter = ''});
  final Map<String, dynamic> me;
  final bool embedded;
  final String defaultFilter;
  @override
  State<StaffJobsScreen> createState() => _StaffJobsScreenState();
}

class _StaffJobsScreenState extends State<StaffJobsScreen> {
  late String _filter = widget.defaultFilter;
  Future<List<dynamic>>? _jobs;

  List<String> get _can => List<String>.from((((widget.me['caps'] as Map?)?['can']) as List?) ?? []);

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _jobs = context.read<AuthProvider>().api.c2cStaffJobs(filter: _filter));

  @override
  Widget build(BuildContext context) {
    final canAssign = _can.contains('assign') || _can.contains('reassign');
    final filters = <List<String>>[
      ['', tr('الكل', 'All')],
      ['today', tr('اليوم', 'Today')],
      ['open', tr('قيد التنفيذ', 'Active')],
      ['done', tr('منجزة', 'Done')],
      if (canAssign) ['unassigned', tr('غير مُسندة', 'Unassigned')],
    ];
    final body = Column(children: [
      SizedBox(
        height: 46,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7), children: [
          for (final f in filters) Padding(
            padding: const EdgeInsets.only(left: 7),
            child: ChoiceChip(
              label: Text(f[1]),
              selected: _filter == f[0],
              onSelected: (_) { setState(() => _filter = f[0]); _load(); },
              selectedColor: Crew.teal,
              labelStyle: TextStyle(color: _filter == f[0] ? Colors.white : Crew.ink, fontWeight: FontWeight.w700, fontSize: 12.5),
              backgroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: _filter == f[0] ? Crew.teal : Colors.black12)),
            ),
          ),
        ]),
      ),
      Expanded(child: RefreshIndicator(
        color: Crew.teal,
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _jobs,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: Crew.teal));
            final jobs = snap.data!;
            if (jobs.isEmpty) {
              return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90), child: Column(children: [
                const Icon(Icons.assignment_turned_in_outlined, size: 60, color: Crew.slate),
                const SizedBox(height: 10),
                Text(tr('لا توجد مهام هنا', 'No jobs here'), style: const TextStyle(color: Crew.slate, fontWeight: FontWeight.w700)),
              ]))]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
              itemCount: jobs.length,
              itemBuilder: (_, i) => _jobCard(jobs[i] as Map),
            );
          },
        ),
      )),
    ]);

    if (widget.embedded) {
      return SafeArea(child: Column(children: [
        _header(),
        Expanded(child: body),
      ]));
    }
    return Scaffold(backgroundColor: Crew.bg, appBar: AppBar(backgroundColor: Crew.teal, foregroundColor: Colors.white, title: Text(tr('المهام', 'Jobs'))), body: body);
  }

  Widget _header() => Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: const BoxDecoration(gradient: LinearGradient(colors: [Crew.teal, Crew.deep], begin: Alignment.topRight, end: Alignment.bottomLeft)),
        child: Row(children: [
          const Icon(Icons.assignment_rounded, color: Colors.white),
          const SizedBox(width: 8),
          Text(widget.defaultFilter == 'today' ? tr('مهام اليوم', "Today's jobs") : tr('كل المهام', 'All jobs'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          const Spacer(),
          Text('${widget.me['role_label']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _jobCard(Map j) {
    final st = '${j['state']}';
    final c = Crew.stateColor(st);
    return GestureDetector(
      onTap: () async {
        final changed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => StaffJobDetail(id: j['id'] as int, me: widget.me)));
        if (changed == true) _load();
      },
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Row(children: [
          Container(width: 5, height: 84, decoration: BoxDecoration(color: c, borderRadius: const BorderRadius.horizontal(left: Radius.circular(16)))),
          Expanded(child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text('${j['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 16)),
                const SizedBox(width: 6),
                Expanded(child: Text('${j['service'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: Crew.ink))),
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)), child: Text('${j['state_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 10.5))),
              ]),
              const SizedBox(height: 6),
              Row(children: [
                const Icon(Icons.person_outline, size: 13, color: Crew.slate),
                const SizedBox(width: 3),
                Expanded(child: Text('${j['customer'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Crew.slate))),
                const Icon(Icons.schedule, size: 13, color: Crew.slate),
                const SizedBox(width: 3),
                Text(_shortTime('${j['visit'] ?? ''}'), style: const TextStyle(fontSize: 11.5, color: Crew.slate, fontWeight: FontWeight.w600)),
              ]),
              if (j['area'] != null || j['address'] != null) ...[
                const SizedBox(height: 3),
                Row(children: [
                  const Icon(Icons.place_outlined, size: 13, color: Crew.slate),
                  const SizedBox(width: 3),
                  Expanded(child: Text('${j['area'] ?? j['address']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: Crew.slate))),
                  if (j['provider'] != null && '${widget.me['name']}' != '${j['provider']}') Text('👷 ${j['provider']}', style: const TextStyle(fontSize: 10.5, color: Crew.teal, fontWeight: FontWeight.w700)),
                ]),
              ],
            ]),
          )),
        ]),
      ),
    );
  }

  String _shortTime(String dt) {
    if (dt.length >= 16) return dt.substring(5, 16); // MM-DD HH:MM
    return dt;
  }
}

/// Role-gated job detail. The action buttons shown depend on the crew member's
/// capabilities: a worker starts/completes and adds proof; a leader/supervisor
/// can also assign and sign off quality; ops/supervisor can approve closure.
class StaffJobDetail extends StatefulWidget {
  const StaffJobDetail({super.key, required this.id, required this.me});
  final int id;
  final Map<String, dynamic> me;
  @override
  State<StaffJobDetail> createState() => _StaffJobDetailState();
}

class _StaffJobDetailState extends State<StaffJobDetail> {
  Map<String, dynamic>? _j;
  bool _busy = false;
  bool _dirty = false;

  List<String> get _can => List<String>.from((((widget.me['caps'] as Map?)?['can']) as List?) ?? []);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final d = await context.read<AuthProvider>().api.c2cStaffJob(widget.id);
    if (mounted) setState(() => _j = d);
  }

  Future<void> _act(String act, {Map<String, dynamic>? body}) async {
    setState(() => _busy = true);
    try {
      final d = await context.read<AuthProvider>().api.c2cStaffJobAction(widget.id, act, body: body);
      _dirty = true;
      if (mounted) setState(() => _j = d);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFC0392B)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Assign the job either to a whole crew (every member + its driver is
  /// notified and sees it) or to one individual.
  Future<void> _assign() async {
    final api = context.read<AuthProvider>().api;
    List<dynamic> teams = const [];
    List<dynamic> members = const [];
    try {
      teams = await api.c2cStaffTeams();
    } catch (_) {}
    try {
      members = await api.c2cStaffTeam();
    } catch (_) {}
    if (!mounted) return;
    final res = await showModalBottomSheet<Map<String, dynamic>>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => DefaultTabController(
        length: 2,
        child: DraggableScrollableSheet(
          expand: false, initialChildSize: 0.75, minChildSize: 0.5, maxChildSize: 0.95,
          builder: (_, sc) => Container(
            decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              Container(
                padding: const EdgeInsets.fromLTRB(18, 12, 18, 0),
                color: Crew.teal,
                child: Column(children: [
                  Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 10), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.person_add_alt_1, color: Colors.white),
                    const SizedBox(width: 10),
                    Expanded(child: Text(tr('إسناد الطلب', 'Assign job'), style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                  ]),
                  TabBar(indicatorColor: Colors.white, labelColor: Colors.white, unselectedLabelColor: Colors.white70,
                    labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
                    tabs: [Tab(text: tr('فريق كامل', 'A crew')), Tab(text: tr('فرد', 'One person'))]),
                ]),
              ),
              Expanded(child: TabBarView(children: [
                // ---- crews ----
                teams.isEmpty
                    ? Center(child: Text(tr('لا فرق معرّفة', 'No crews defined'), style: const TextStyle(color: Crew.slate)))
                    : ListView(controller: sc, padding: const EdgeInsets.all(12), children: [
                        for (final t in teams) _crewTile(ctx, t as Map),
                      ]),
                // ---- individuals ----
                members.isEmpty
                    ? Center(child: Text(tr('لا أعضاء', 'No members'), style: const TextStyle(color: Crew.slate)))
                    : ListView(padding: const EdgeInsets.all(12), children: [
                        for (final m in members) ListTile(
                          leading: CircleAvatar(backgroundColor: Crew.teal.withValues(alpha: 0.12), child: Text('${m['name']}'.characters.first, style: const TextStyle(color: Crew.teal, fontWeight: FontWeight.w800))),
                          title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text('${m['role_label']} · ${tr('مهام مفتوحة', 'open')}: ${m['load']}'),
                          trailing: m['available'] == true ? const Icon(Icons.check_circle, color: Crew.green, size: 18) : const Icon(Icons.do_not_disturb_on, color: Crew.slate, size: 18),
                          onTap: () => Navigator.pop(ctx, {'provider_id': m['id']}),
                        ),
                      ]),
              ])),
            ]),
          ),
        ),
      ),
    );
    if (res != null) await _act(_j?['provider_id'] != null ? 'reassign' : 'assign', body: res);
  }

  /// One crew: status, its driver, and every member's availability + load.
  Widget _crewTile(BuildContext ctx, Map t) {
    const statusColors = {'free': Crew.green, 'busy': Crew.amber, 'off': Crew.slate};
    final c = statusColors['${t['status']}'] ?? Crew.slate;
    final statusLabel = {'free': tr('متاح', 'Free'), 'busy': tr('مشغول', 'Busy'), 'off': tr('غير متاح', 'Off')}['${t['status']}'] ?? '';
    final driver = t['driver'] as Map?;
    final members = (t['members'] as List?) ?? const [];
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade300)),
      child: Column(children: [
        ListTile(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          leading: CircleAvatar(backgroundColor: c.withValues(alpha: 0.14), child: Icon(Icons.groups_rounded, color: c)),
          title: Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Crew.ink)),
          subtitle: Text('${t['size']} ${tr('عضو', 'members')} · ${tr('مهام جارية', 'active')}: ${t['active_jobs']}'),
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
            child: Text(statusLabel, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 11)),
          ),
          onTap: () => Navigator.pop(ctx, {'team_leader_id': t['id']}),
        ),
        if (driver != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: Row(children: [
              const Icon(Icons.local_shipping_rounded, size: 15, color: Crew.blue),
              const SizedBox(width: 6),
              Expanded(child: Text('${tr('السائق', 'Driver')}: ${driver['name']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Crew.ink))),
              Icon(driver['available'] == true ? Icons.check_circle : Icons.do_not_disturb_on,
                  size: 15, color: driver['available'] == true ? Crew.green : Crew.slate),
            ]),
          ),
        if (members.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
            child: Wrap(spacing: 6, runSpacing: 6, children: [
              for (final m in members)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: (m['available'] == true ? Crew.green : Crew.slate).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8)),
                  child: Text('${m['name']} · ${m['load']}',
                      style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800,
                          color: m['available'] == true ? Crew.green : Crew.slate)),
                ),
            ]),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) { if (!didPop) Navigator.pop(context, _dirty); },
      child: Scaffold(
        backgroundColor: Crew.bg,
        appBar: AppBar(backgroundColor: Crew.teal, foregroundColor: Colors.white, title: Text(tr('تفاصيل المهمة', 'Job detail')), leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => Navigator.pop(context, _dirty))),
        body: _j == null
            ? const Center(child: CircularProgressIndicator(color: Crew.teal))
            : _content(_j!),
        bottomNavigationBar: _j == null ? null : _actionBar(_j!),
      ),
    );
  }

  Widget _content(Map j) {
    final st = '${j['state']}';
    final c = Crew.stateColor(st);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('${j['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 26)),
            const SizedBox(width: 8),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${j['service'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Crew.ink)),
              Text('${j['name'] ?? ''} · ${j['category'] ?? ''}', style: const TextStyle(fontSize: 12, color: Crew.slate)),
            ])),
            Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)), child: Text('${j['state_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 11.5))),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      _card(tr('العميل والموقع', 'Customer & location'), [
        _kv(Icons.person_outline, tr('العميل', 'Customer'), j['customer']),
        _kvAction(Icons.phone_outlined, tr('الهاتف', 'Phone'), j['phone'], j['phone'] != null ? Icons.call : null),
        _kv(Icons.place_outlined, tr('العنوان', 'Address'), j['address']),
        _kv(Icons.map_outlined, tr('المنطقة', 'Area'), j['area']),
        _kv(Icons.schedule, tr('الموعد', 'Visit'), j['visit']),
      ]),
      const SizedBox(height: 12),
      _card(tr('التنفيذ', 'Execution'), [
        _kv(Icons.badge_outlined, tr('المنفّذ', 'Assigned to'), j['provider']),
        _kv(Icons.play_circle_outline, tr('بدأ', 'Started'), j['started_at']),
        _kv(Icons.flag_outlined, tr('انتهى', 'Finished'), j['finished_at']),
        if (j['staff_note'] != null) _kv(Icons.sticky_note_2_outlined, tr('ملاحظة الفريق', 'Crew note'), j['staff_note']),
        if (j['quality_ok'] == true) _kv(Icons.verified_outlined, tr('الجودة', 'Quality'), tr('معتمدة ✓', 'Approved ✓')),
      ]),
      const SizedBox(height: 12),
      _proofRow(j),
      if (j['notes'] != null) ...[const SizedBox(height: 12), _card(tr('ملاحظات العميل', 'Customer notes'), [Text('${j['notes']}', style: const TextStyle(fontSize: 13, height: 1.4))])],
      const SizedBox(height: 90),
    ]);
  }

  /// Before/after evidence: as many photos and videos as the job needs.
  Widget _proofRow(Map j) {
    final media = ((j['media'] as List?) ?? const []).cast<Map>();
    final before = media.where((m) => m['kind'] == 'before').toList();
    final after = media.where((m) => m['kind'] == 'after').toList();
    final canAdd = _can.contains('proof');
    return _card(tr('توثيق التنفيذ (قبل / بعد)', 'Before / after evidence'), [
      _gallery(tr('قبل', 'Before'), before, 'before', canAdd, Crew.amber),
      const SizedBox(height: 14),
      _gallery(tr('بعد', 'After'), after, 'after', canAdd, Crew.green),
    ]);
  }

  Widget _gallery(String label, List<Map> items, String kind, bool canAdd, Color c) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w900, color: Crew.ink)),
        const SizedBox(width: 6),
        Text('(${items.length})', style: const TextStyle(fontSize: 11.5, color: Crew.slate, fontWeight: FontWeight.w700)),
      ]),
      const SizedBox(height: 7),
      SizedBox(height: 88, child: ListView(scrollDirection: Axis.horizontal, children: [
        if (canAdd)
          GestureDetector(
            onTap: () => _addMedia(kind),
            child: Container(
              width: 84, height: 84, margin: const EdgeInsets.only(left: 8),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(13), border: Border.all(color: c.withValues(alpha: 0.35))),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(Icons.add_a_photo_rounded, color: c, size: 22),
                const SizedBox(height: 4),
                Text(tr('إضافة', 'Add'), style: TextStyle(fontSize: 10.5, color: c, fontWeight: FontWeight.w800)),
              ]),
            ),
          ),
        for (final m in items)
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: GestureDetector(
              onTap: () async {
                final tok = await context.read<AuthProvider>().api.token;
                if (!mounted) return;
                Navigator.push(context, MaterialPageRoute(
                    builder: (_) => MediaViewerScreen(media: items, index: items.indexOf(m), token: tok)));
              },
              child: Container(
                width: 84, height: 84, clipBehavior: Clip.antiAlias,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), color: Colors.black12),
                child: m['is_video'] == true
                    ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Color(0xFFE5484D), size: 32))
                    : _AuthImage(url: '${m['thumb'] ?? m['url']}'),
              ),
            ),
          ),
        if (items.isEmpty && !canAdd)
          Container(width: 120, alignment: Alignment.center, child: Text(tr('لا توجد', 'None'), style: const TextStyle(color: Crew.slate, fontSize: 12))),
      ])),
    ]);
  }

  /// Capture or pick one or more photos/videos for the before/after gallery.
  Future<void> _addMedia(String kind) async {
    final choice = await showModalBottomSheet<String>(context: context, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => SafeArea(child: Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera_rounded, color: Crew.teal), title: Text(tr('التقاط صورة', 'Take photo')), onTap: () => Navigator.pop(ctx, 'cam_photo')),
        ListTile(leading: const Icon(Icons.videocam_rounded, color: Color(0xFFE5484D)), title: Text(tr('تسجيل فيديو', 'Record video')), onTap: () => Navigator.pop(ctx, 'cam_video')),
        ListTile(leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF7C3AED)), title: Text(tr('صور من المعرض (متعددة)', 'Photos from gallery')), onTap: () => Navigator.pop(ctx, 'gal_photos')),
        ListTile(leading: const Icon(Icons.video_library_rounded, color: Crew.blue), title: Text(tr('فيديو من المعرض', 'Video from gallery')), onTap: () => Navigator.pop(ctx, 'gal_video')),
      ])));
    if (choice == null) return;
    final picker = ImagePicker();
    final items = <Map<String, dynamic>>[];
    try {
      if (choice == 'cam_photo') {
        final x = await picker.pickImage(source: ImageSource.camera, imageQuality: 70, maxWidth: 1600);
        if (x != null) items.add({'kind': kind, 'media_type': 'photo', 'name': x.name, 'data': base64Encode(await x.readAsBytes())});
      } else if (choice == 'gal_photos') {
        final xs = await picker.pickMultiImage(imageQuality: 70, maxWidth: 1600);
        for (final x in xs) {
          items.add({'kind': kind, 'media_type': 'photo', 'name': x.name, 'data': base64Encode(await x.readAsBytes())});
        }
      } else {
        final x = await picker.pickVideo(
            source: choice == 'cam_video' ? ImageSource.camera : ImageSource.gallery,
            maxDuration: const Duration(seconds: 45));
        if (x != null) {
          final b = await x.readAsBytes();
          if (b.length > 15 * 1024 * 1024) {
            if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('الفيديو كبير جداً (الحد 15 ميجا)', 'Video too large (max 15 MB)'))));
            return;
          }
          items.add({'kind': kind, 'media_type': 'video', 'name': x.name, 'data': base64Encode(b)});
        }
      }
      if (items.isEmpty) return;
      await _act('media', body: {'media': items});
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  /// Crew declares the job finished → it goes to the supervisor for sign-off.
  Future<void> _finish() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('إنهاء وإرسال للاعتماد', 'Finish & send for approval')),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(tr('سيراجع المشرف صور قبل/بعد ويعتمد الإنجاز.', 'The supervisor reviews the before/after evidence and signs it off.'),
            style: const TextStyle(fontSize: 13)),
        const SizedBox(height: 10),
        TextField(controller: ctrl, maxLines: 2, decoration: InputDecoration(hintText: tr('ملاحظة الفريق (اختياري)', 'Crew note (optional)'), border: const OutlineInputBorder())),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: Crew.green), onPressed: () => Navigator.pop(c, true), child: Text(tr('إرسال', 'Send'))),
      ],
    ));
    if (ok != true) return;
    if (ctrl.text.trim().isNotEmpty) await _act('note', body: {'note': ctrl.text.trim()});
    await _act('finish');
  }

  /// Supervisor signs the job off (or sends it back with a reason).
  Future<void> _review(bool approve) async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(approve ? tr('اعتماد الإنجاز', 'Approve completion') : tr('إعادة للتنفيذ', 'Send back')),
      content: TextField(controller: ctrl, maxLines: 3, decoration: InputDecoration(
          hintText: approve ? tr('ملاحظة (اختياري)', 'Note (optional)') : tr('سبب الإعادة', 'Reason'),
          border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: approve ? Crew.green : const Color(0xFFE5484D)),
          onPressed: () => Navigator.pop(c, true),
          child: Text(approve ? tr('اعتماد', 'Approve') : tr('إعادة', 'Return'))),
      ],
    ));
    if (ok != true) return;
    await _act(approve ? 'approve_completion' : 'reject_completion', body: {'note': ctrl.text.trim()});
  }

  Widget _actionBar(Map j) {
    final st = '${j['state']}';
    final btns = <Widget>[];
    Widget b(String label, IconData ic, Color col, VoidCallback? on) => Expanded(child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: ElevatedButton.icon(
            onPressed: _busy ? null : on,
            icon: Icon(ic, size: 18),
            label: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            style: ElevatedButton.styleFrom(backgroundColor: col, foregroundColor: Colors.white, minimumSize: const Size.fromHeight(48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
          ),
        ));

    if (st == 'assigned' && _can.contains('start')) btns.add(b(tr('بدء التنفيذ', 'Start'), Icons.play_arrow_rounded, Crew.amber, () => _act('start')));
    // the crew finishes → the supervisor reviews the before/after evidence
    if (st == 'in_progress' && _can.contains('complete')) btns.add(b(tr('أنهيت العمل', 'Finished'), Icons.check_rounded, Crew.green, _finish));
    if (st == 'review' && (_can.contains('quality') || _can.contains('approve'))) {
      btns.add(b(tr('إعادة', 'Return'), Icons.undo_rounded, const Color(0xFFE5484D), () => _review(false)));
      btns.add(b(tr('اعتماد', 'Approve'), Icons.verified_rounded, Crew.green, () => _review(true)));
    }
    if ((st == 'confirmed' || st == 'assigned') && (_can.contains('assign') || _can.contains('reassign'))) btns.add(b(j['provider_id'] != null ? tr('إعادة إسناد', 'Reassign') : tr('إسناد', 'Assign'), Icons.person_add_alt_1, Crew.blue, _assign));
    if (st == 'done' && _can.contains('quality') && j['quality_ok'] != true) btns.add(b(tr('اعتماد الجودة', 'Quality OK'), Icons.verified, const Color(0xFF7C3AED), () => _act('quality')));
    if (st == 'done' && _can.contains('approve')) btns.add(b(tr('اعتماد الإغلاق', 'Approve'), Icons.done_all_rounded, Crew.deep, () => _act('approve')));

    if (btns.isEmpty) return const SizedBox.shrink();
    return SafeArea(child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      decoration: const BoxDecoration(color: Colors.white, boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))]),
      child: Row(children: btns),
    ));
  }

  Widget _card(String title, List<Widget> children) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Container(width: 4, height: 15, decoration: BoxDecoration(color: Crew.teal, borderRadius: BorderRadius.circular(3))), const SizedBox(width: 7), Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Crew.ink))]),
          const SizedBox(height: 10),
          ...children,
        ]),
      );

  Widget _kv(IconData ic, String k, dynamic v) => (v == null || '$v'.isEmpty) ? const SizedBox.shrink() : Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(ic, size: 16, color: Crew.slate), const SizedBox(width: 8), SizedBox(width: 90, child: Text(k, style: const TextStyle(color: Crew.slate, fontSize: 12))), Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Crew.ink)))]),
      );

  Widget _kvAction(IconData ic, String k, dynamic v, IconData? action) => (v == null || '$v'.isEmpty) ? const SizedBox.shrink() : Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [Icon(ic, size: 16, color: Crew.slate), const SizedBox(width: 8), SizedBox(width: 90, child: Text(k, style: const TextStyle(color: Crew.slate, fontSize: 12))), Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Crew.ink))), if (action != null) Icon(action, size: 17, color: Crew.teal)]),
      );
}


/// Media served by the API needs the app token, so plain Image.network fails.
class _AuthImage extends StatelessWidget {
  const _AuthImage({required this.url});
  final String url;
  @override
  Widget build(BuildContext context) => FutureBuilder<String?>(
        future: context.read<AuthProvider>().api.token,
        builder: (_, snap) => snap.hasData
            ? Image.network(url, fit: BoxFit.cover, width: double.infinity,
                headers: {'Authorization': 'Bearer ${snap.data}'},
                errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_rounded, color: Crew.slate))
            : const SizedBox.shrink(),
      );
}
