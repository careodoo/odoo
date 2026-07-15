import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
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

  Future<void> _proof(String kind) async {
    final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 70, maxWidth: 1280);
    if (x == null) return;
    final b64 = base64Encode(await File(x.path).readAsBytes());
    await _act('proof', body: {'kind': kind, 'image': b64});
  }

  Future<void> _complete() async {
    final note = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('إنهاء المهمة', 'Complete job')),
      content: TextField(controller: note, maxLines: 3, decoration: InputDecoration(hintText: tr('ملاحظة (اختياري)', 'Note (optional)'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Crew.green), onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إنهاء', 'Complete'), style: const TextStyle(color: Colors.white))),
      ],
    ));
    if (ok == true) await _act('complete', body: {'note': note.text});
  }

  Future<void> _assign() async {
    final team = await context.read<AuthProvider>().api.c2cStaffTeam();
    if (!mounted) return;
    final picked = await showModalBottomSheet<int>(context: context, backgroundColor: Colors.white, shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))), builder: (ctx) => ListView(shrinkWrap: true, padding: const EdgeInsets.all(12), children: [
      Padding(padding: const EdgeInsets.all(8), child: Text(tr('إسناد إلى عضو الفريق', 'Assign to member'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Crew.ink))),
      for (final m in team) ListTile(
        leading: CircleAvatar(backgroundColor: Crew.teal.withValues(alpha: 0.12), child: Text('${m['name']}'.characters.first, style: const TextStyle(color: Crew.teal, fontWeight: FontWeight.w800))),
        title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${m['role_label']} · ${tr('مهام مفتوحة', 'open')}: ${m['load']}'),
        trailing: m['available'] == true ? const Icon(Icons.check_circle, color: Crew.green, size: 18) : const Icon(Icons.do_not_disturb_on, color: Crew.slate, size: 18),
        onTap: () => Navigator.pop(ctx, m['id'] as int),
      ),
    ]));
    if (picked != null) await _act(_j?['provider_id'] != null ? 'reassign' : 'assign', body: {'provider_id': picked});
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

  Widget _proofRow(Map j) {
    Widget slot(String label, String? url, String kind) => Expanded(child: Column(children: [
          Text(label, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Crew.slate)),
          const SizedBox(height: 5),
          GestureDetector(
            onTap: _can.contains('proof') ? () => _proof(kind) : null,
            child: Container(
              height: 96,
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
              clipBehavior: Clip.antiAlias,
              child: url != null
                  ? Image.network(url, fit: BoxFit.cover, width: double.infinity)
                  : Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Icon(_can.contains('proof') ? Icons.add_a_photo_outlined : Icons.image_outlined, color: Crew.slate), if (_can.contains('proof')) Padding(padding: const EdgeInsets.only(top: 4), child: Text(tr('التقط', 'Capture'), style: const TextStyle(fontSize: 10, color: Crew.slate)))])),
            ),
          ),
        ]));
    return _card(tr('صور الإثبات', 'Proof photos'), [
      Row(children: [slot(tr('قبل', 'Before'), j['before'], 'before'), const SizedBox(width: 10), slot(tr('بعد', 'After'), j['after'], 'after')]),
    ]);
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
    if (st == 'in_progress' && _can.contains('complete')) btns.add(b(tr('إنهاء', 'Complete'), Icons.check_rounded, Crew.green, _complete));
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
