import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';

/// شاشة «التوقيع الإلكتروني» (لمدير منظومة التواقيع):
///  • الخطوة 1 — بحث واختيار موظّف (قائمة بها الاسم/الرقم الوظيفي/القسم/المسمّى).
///  • الخطوة 2 — لوحة توقيع باللمس (canvas) → حفظ الصورة في ملف الموظّف عبر /esign/enroll.
///  • تبويب «آخر الاعتمادات» يعرض سجلّ care.esign.enrollment.
/// الباك-اند يمنع غير المخوّل برسالة 403 واضحة؛ نعرضها كما هي.
class EsignScreen extends StatefulWidget {
  const EsignScreen({super.key});
  @override
  State<EsignScreen> createState() => _EsignScreenState();
}

// ===== هوية التطبيق =====
const _navy = Color(0xFF0E3A5F);
const _green = Color(0xFF15803D);
const _ink = Color(0xFF182131);
const _slate = Color(0xFF5B677B);
const _bg = Color(0xFFF4F7FB);
const _red = Color(0xFFB91C1C);

class _EsignScreenState extends State<EsignScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: _bg,
        appBar: AppBar(
          backgroundColor: _navy, foregroundColor: Colors.white, elevation: 0,
          title: Text(tr('التوقيع الإلكتروني', 'E-signature'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
          bottom: TabBar(
            controller: _tabs,
            indicatorColor: Colors.white, indicatorWeight: 3,
            labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
            unselectedLabelColor: Colors.white70,
            tabs: [
              Tab(text: tr('تسجيل توقيع', 'Enroll signature')),
              Tab(text: tr('آخر الاعتمادات', 'Recent enrollments')),
            ],
          ),
        ),
        body: TabBarView(
          controller: _tabs,
          children: const [
            _EnrollTab(),
            _EnrollmentsTab(),
          ],
        ),
      ),
    );
  }
}

// =========================== تبويب التسجيل (اختيار موظّف + توقيع) ===========================
class _EnrollTab extends StatefulWidget {
  const _EnrollTab();
  @override
  State<_EnrollTab> createState() => _EnrollTabState();
}

class _EnrollTabState extends State<_EnrollTab> {
  final _searchCtrl = TextEditingController();
  final _padKey = GlobalKey<_SignaturePadState>();
  Timer? _debounce;

  bool _loading = true;
  String? _err;
  int? _errStatus;
  List<Map> _employees = const [];
  Map? _selected; // الموظّف المختار (الخطوة 2)
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load({String? q}) async {
    setState(() { _loading = true; _err = null; _errStatus = null; });
    try {
      final d = await context.read<AuthProvider>().api.esignMeta(q: q);
      if (!mounted) return;
      setState(() {
        _employees = ((d['employees'] as List?) ?? const []).cast<Map>();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _err = e is ApiException ? e.message : '$e';
        _errStatus = e is ApiException ? e.status : null;
        _loading = false;
      });
    }
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 420), () => _load(q: v));
  }

  void _snack(String msg, {bool bad = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg), backgroundColor: bad ? _red : _green,
      behavior: SnackBarBehavior.floating, duration: const Duration(milliseconds: 2200)));
  }

  Future<void> _save() async {
    final emp = _selected;
    final pad = _padKey.currentState;
    if (emp == null || pad == null) return;
    if (pad.isEmpty) {
      _snack(tr('الرجاء التوقيع على اللوحة أولًا', 'Please draw a signature first'), bad: true);
      return;
    }
    setState(() => _saving = true);
    final api = context.read<AuthProvider>().api;
    try {
      final bytes = await pad.exportPng();
      if (bytes == null) throw Exception(tr('تعذّر تصدير التوقيع', 'Could not export signature'));
      final b64 = base64Encode(bytes);
      final d = await api.esignEnroll(emp['employee_id'] as int, b64);
      final serial = '${d['serial'] ?? ''}';
      final who = '${d['employee'] ?? emp['name'] ?? ''}';
      _snack(tr('حُفظ توقيع $who${serial.isEmpty ? '' : ' — $serial'}',
               'Saved $who\'s signature${serial.isEmpty ? '' : ' — $serial'}'));
      if (!mounted) return;
      // أفرِغ وأعِد لاختيار موظّف، وأعِد تحميل القائمة (تحديث شارة «له توقيع»).
      pad.clear();
      setState(() { _selected = null; _saving = false; });
      _load(q: _searchCtrl.text);
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      _snack(e is ApiException ? e.message : '$e', bad: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_selected != null) return _signStep(_selected!);
    // الخطوة 1 — اختيار الموظّف
    return Column(children: [
      _searchBar(),
      Expanded(child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _err != null
              ? _errorView()
              : _employees.isEmpty
                  ? _emptyView()
                  : RefreshIndicator(
                      onRefresh: () => _load(q: _searchCtrl.text),
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 6, 12, 24),
                        itemCount: _employees.length,
                        itemBuilder: (_, i) => _employeeCard(_employees[i]),
                      ),
                    )),
    ]);
  }

  Widget _searchBar() => Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
        child: TextField(
          controller: _searchCtrl,
          onChanged: _onSearch,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            isDense: true,
            hintText: tr('ابحث بالاسم أو الرقم الوظيفي…', 'Search by name or ID…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            suffixIcon: _searchCtrl.text.isEmpty ? null : IconButton(
              icon: const Icon(Icons.close_rounded, size: 18),
              onPressed: () { _searchCtrl.clear(); _load(); setState(() {}); }),
            filled: true, fillColor: _bg,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
      );

  Widget _employeeCard(Map e) {
    final name = '${e['name'] ?? ''}';
    final barcode = '${e['barcode'] ?? ''}';
    final job = '${e['job'] ?? ''}';
    final dept = '${e['department'] ?? ''}';
    final has = e['has_signature'] == true;
    final initial = name.trim().isEmpty ? '؟' : name.trim().characters.first;
    return Container(
      margin: const EdgeInsets.only(bottom: 9),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 10, offset: Offset(0, 3))]),
      child: Material(color: Colors.transparent, child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () { _padKey.currentState?.clear(); setState(() => _selected = e); },
        child: Padding(padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
          child: Row(children: [
            CircleAvatar(radius: 22, backgroundColor: _navy,
              child: Text(initial, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _ink))),
                if (has) Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: _green.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text('✓ ${tr('له توقيع', 'Signed')}',
                      style: const TextStyle(color: _green, fontWeight: FontWeight.w800, fontSize: 10.5))),
              ]),
              const SizedBox(height: 3),
              Wrap(spacing: 6, runSpacing: 3, children: [
                if (barcode.isNotEmpty) _chip(Icons.badge_outlined, barcode),
                if (job.isNotEmpty) _chip(Icons.work_outline_rounded, job),
                if (dept.isNotEmpty) _chip(Icons.apartment_rounded, dept),
              ]),
            ])),
            const Icon(Icons.chevron_left_rounded, color: _slate),
          ]),
        ),
      )),
    );
  }

  Widget _chip(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: _bg, borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFFEEF2F7))),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 12, color: _slate),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(fontSize: 10.5, color: _ink)),
        ]),
      );

  // ---- الخطوة 2: لوحة التوقيع ----
  Widget _signStep(Map emp) {
    final name = '${emp['name'] ?? ''}';
    final barcode = '${emp['barcode'] ?? ''}';
    return Column(children: [
      // رأس الموظّف المختار + رجوع
      Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(8, 8, 14, 12),
        child: Row(children: [
          IconButton(
            icon: const Icon(Icons.arrow_forward_rounded, color: _navy),
            tooltip: tr('رجوع', 'Back'),
            onPressed: _saving ? null : () => setState(() => _selected = null)),
          CircleAvatar(radius: 20, backgroundColor: _navy,
            child: Text(name.trim().isEmpty ? '؟' : name.trim().characters.first,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: _ink)),
            if (barcode.isNotEmpty) Text(barcode, style: const TextStyle(fontSize: 12, color: _slate)),
          ])),
        ]),
      ),
      Expanded(child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(children: [
          Align(alignment: AlignmentDirectional.centerStart, child: Text(
            tr('وقّع داخل الإطار أدناه', 'Sign inside the frame below'),
            style: const TextStyle(fontWeight: FontWeight.w800, color: _slate, fontSize: 12.5))),
          const SizedBox(height: 8),
          Expanded(child: Container(
            decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFD7DEE8), width: 1.4),
              boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 10, offset: Offset(0, 3))]),
            clipBehavior: Clip.antiAlias,
            child: _SignaturePad(key: _padKey),
          )),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: OutlinedButton.icon(
              onPressed: _saving ? null : () => _padKey.currentState?.clear(),
              icon: const Icon(Icons.refresh_rounded, size: 18, color: _slate),
              style: OutlinedButton.styleFrom(foregroundColor: _slate,
                side: const BorderSide(color: Color(0xFFCBD5E1)), minimumSize: const Size.fromHeight(50)),
              label: Text(tr('مسح', 'Clear'), style: const TextStyle(fontWeight: FontWeight.w900)))),
            const SizedBox(width: 12),
            Expanded(flex: 2, child: FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.save_rounded, size: 19),
              style: FilledButton.styleFrom(backgroundColor: _green, minimumSize: const Size.fromHeight(50)),
              label: Text(_saving ? tr('جارٍ الحفظ…', 'Saving…') : tr('حفظ التوقيع', 'Save signature'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)))),
          ]),
        ]),
      )),
    ]);
  }

  Widget _errorView() {
    final is403 = _errStatus == 403;
    return Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
      mainAxisSize: MainAxisSize.min, children: [
        Icon(is403 ? Icons.lock_outline_rounded : Icons.cloud_off_rounded, size: 48, color: _slate),
        const SizedBox(height: 12),
        Text(is403
                ? tr('هذه الميزة لمدير منظومة التواقيع', 'This feature is for the e-signature manager')
                : tr('تعذّر التحميل', 'Could not load'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w900, color: _ink)),
        if (!is403) ...[
          const SizedBox(height: 6),
          Text('$_err', textAlign: TextAlign.center, style: const TextStyle(color: _slate, fontSize: 12)),
          const SizedBox(height: 16),
          FilledButton.icon(onPressed: () => _load(q: _searchCtrl.text),
            icon: const Icon(Icons.refresh_rounded), label: Text(tr('إعادة المحاولة', 'Retry'))),
        ],
      ])));
  }

  Widget _emptyView() => Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
    mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.person_search_rounded, size: 50, color: _slate),
      const SizedBox(height: 10),
      Text(tr('لا موظّفين مطابقين', 'No matching employees'),
          style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
    ])));
}

// =========================== لوحة التوقيع (canvas) ===========================
class _SignaturePad extends StatefulWidget {
  const _SignaturePad({super.key});
  @override
  State<_SignaturePad> createState() => _SignaturePadState();
}

class _SignaturePadState extends State<_SignaturePad> {
  final GlobalKey _boundaryKey = GlobalKey();
  // كل مسار = سلسلة نقاط مرسومة بإصبع واحد؛ القائمة كلها = اللوحة.
  final List<List<Offset>> _strokes = [];

  bool get isEmpty => _strokes.every((s) => s.isEmpty) || _strokes.isEmpty;

  void clear() => setState(() => _strokes.clear());

  /// يصدّر محتوى اللوحة كـ PNG (خلفية بيضاء) عبر RepaintBoundary.
  Future<Uint8List?> exportPng() async {
    final obj = _boundaryKey.currentContext?.findRenderObject();
    if (obj is! RenderRepaintBoundary) return null;
    final image = await obj.toImage(pixelRatio: 2.5);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return data?.buffer.asUint8List();
  }

  void _start(Offset p) => setState(() => _strokes.add(<Offset>[p]));
  void _update(Offset p) => setState(() { if (_strokes.isNotEmpty) _strokes.last.add(p); });

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      key: _boundaryKey,
      child: GestureDetector(
        onPanStart: (d) => _start(d.localPosition),
        onPanUpdate: (d) => _update(d.localPosition),
        behavior: HitTestBehavior.opaque,
        child: CustomPaint(
          painter: _SignaturePainter(_strokes),
          size: Size.infinite,
          child: isEmpty
              ? Center(child: IgnorePointer(child: Text(
                  tr('وقّع هنا', 'Sign here'),
                  style: TextStyle(color: Colors.grey.shade300, fontWeight: FontWeight.w900, fontSize: 22))))
              : const SizedBox.expand(),
        ),
      ),
    );
  }
}

class _SignaturePainter extends CustomPainter {
  _SignaturePainter(this.strokes);
  final List<List<Offset>> strokes;

  @override
  void paint(Canvas canvas, Size size) {
    // خلفية بيضاء (مهمّة لتصدير PNG بخلفية صلبة)
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    final pen = Paint()
      ..color = Colors.black
      ..strokeWidth = 3.2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;
    for (final s in strokes) {
      if (s.isEmpty) continue;
      if (s.length == 1) {
        canvas.drawPoints(ui.PointMode.points, s, pen);
        continue;
      }
      final path = Path()..moveTo(s.first.dx, s.first.dy);
      for (var i = 1; i < s.length; i++) {
        path.lineTo(s[i].dx, s[i].dy);
      }
      canvas.drawPath(path, pen);
    }
  }

  @override
  bool shouldRepaint(_SignaturePainter old) => true;
}

// =========================== تبويب آخر الاعتمادات ===========================
class _EnrollmentsTab extends StatefulWidget {
  const _EnrollmentsTab();
  @override
  State<_EnrollmentsTab> createState() => _EnrollmentsTabState();
}

class _EnrollmentsTabState extends State<_EnrollmentsTab> {
  bool _loading = true;
  String? _err;
  int? _errStatus;
  List<Map> _rows = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; _errStatus = null; });
    try {
      final d = await context.read<AuthProvider>().api.esignEnrollments();
      if (!mounted) return;
      setState(() {
        _rows = ((d['enrollments'] as List?) ?? const []).cast<Map>();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _err = e is ApiException ? e.message : '$e';
        _errStatus = e is ApiException ? e.status : null;
        _loading = false;
      });
    }
  }

  Color _stateColor(String s) => switch (s) {
        'active' || 'approved' => _green,
        'rejected' || 'revoked' || 'disabled' => _red,
        'to_approve' || 'submitted' => const Color(0xFFD97706),
        _ => _slate,
      };

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_err != null) {
      final is403 = _errStatus == 403;
      return Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
        mainAxisSize: MainAxisSize.min, children: [
          Icon(is403 ? Icons.lock_outline_rounded : Icons.cloud_off_rounded, size: 48, color: _slate),
          const SizedBox(height: 12),
          Text(is403
                  ? tr('هذه الميزة لمدير منظومة التواقيع', 'This feature is for the e-signature manager')
                  : tr('تعذّر التحميل', 'Could not load'),
              textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w900, color: _ink)),
          if (!is403) ...[
            const SizedBox(height: 16),
            FilledButton.icon(onPressed: _load, icon: const Icon(Icons.refresh_rounded),
              label: Text(tr('إعادة المحاولة', 'Retry'))),
          ],
        ])));
    }
    if (_rows.isEmpty) {
      return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.history_edu_rounded, size: 50, color: _slate),
        const SizedBox(height: 10),
        Text(tr('لا اعتمادات بعد', 'No enrollments yet'),
            style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
      ]));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
        itemCount: _rows.length,
        itemBuilder: (_, i) {
          final r = _rows[i];
          final sc = _stateColor('${r['state'] ?? ''}');
          final serial = '${r['serial'] ?? ''}';
          return Container(
            margin: const EdgeInsets.only(bottom: 9),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
              boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 10, offset: Offset(0, 3))]),
            child: Padding(padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
              child: Row(children: [
                Container(width: 42, height: 42, alignment: Alignment.center,
                  decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                  child: Icon(Icons.draw_rounded, color: sc, size: 20)),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${r['employee'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _ink)),
                  const SizedBox(height: 2),
                  Text('${r['name'] ?? ''}${serial.isEmpty ? '' : ' · $serial'}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11.5, color: _slate)),
                  if ('${r['date'] ?? ''}'.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 2),
                    child: Text('${r['date']}', style: const TextStyle(fontSize: 11, color: _slate))),
                ])),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text('${r['state_label'] ?? r['state'] ?? ''}',
                      style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 11))),
              ]),
            ),
          );
        },
      ),
    );
  }
}
