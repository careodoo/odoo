import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'work_order_detail_screen.dart';
import 'requests_screen.dart';

const _navy = Color(0xFF0E3A5F);

/// How one specialist service presents itself.
///
/// These services are run very differently — a pest programme is about coverage
/// and recurrence, a pool is about water readings, a tank is about certification
/// dates — so the screen is configured per service rather than being one generic
/// list with a different title on top.
class ServiceSpec {
  const ServiceSpec({
    required this.code,
    required this.ar,
    required this.en,
    required this.icon,
    required this.color,
    required this.tagline,
    required this.facts,
    required this.checklist,
  });

  final String code;
  final String ar;
  final String en;
  final String icon;
  final Color color;

  /// One line on what this service actually guarantees the client.
  final (String, String) tagline;

  /// The reference numbers a client is entitled to hold the service to.
  final List<(String, String, String)> facts; // (icon, ar, en)

  /// What the crew is expected to do on every visit.
  final List<(String, String)> checklist; // (ar, en)

  static const pest = ServiceSpec(
    code: 'pest',
    ar: 'مكافحة الحشرات', en: 'Pest control',
    icon: '🐜', color: Color(0xFF7C3AED),
    tagline: ('برنامج وقائي دوري — لا يُنتظر ظهور الحشرة لبدء العلاج',
        'A preventive programme — treatment does not wait for a sighting'),
    facts: [
      ('🧪', 'مبيدات معتمدة من وزارة الصحة فقط', 'Ministry-approved pesticides only'),
      ('🚫', 'لا رشّ في مناطق المرضى أثناء تواجدهم', 'No spraying in occupied patient areas'),
      ('📍', 'مصائد مرقّمة تُفحص أسبوعيًا', 'Numbered bait stations checked weekly'),
      ('📄', 'سجل المواد المستخدمة متاح للعميل', 'Chemical register open to the client'),
    ],
    checklist: [
      ('فحص نقاط التجمّع ومصادر المياه الراكدة', 'Inspect harbourage and standing water'),
      ('تفقّد المصائد وتسجيل ما التُقط', 'Check the traps and log the catch'),
      ('رشّ موضعي في الشقوق والفراغات', 'Targeted crack-and-crevice treatment'),
      ('إغلاق مداخل الحشرات المكتشفة', 'Seal any entry point found'),
      ('توثيق بالصور قبل وبعد', 'Photo evidence before and after'),
    ],
  );

  static const disinfection = ServiceSpec(
    code: 'disinfection',
    ar: 'التعقيم', en: 'Disinfection',
    icon: '🧴', color: Color(0xFF0EA5A5),
    tagline: ('مطهّرات معتمدة من مكافحة العدوى، مع احترام زمن التلامس فعليًا',
        'Infection-control approved products, with the contact time actually observed'),
    facts: [
      ('⏱', 'زمن التلامس لا يقل عن دقيقة', 'Contact time of at least one minute'),
      ('🎯', 'أولوية لأسطح التلامس المتكرر', 'High-touch surfaces take priority'),
      ('🏷️', 'تعقيم نهائي بعد خروج كل مريض', 'Terminal clean after every discharge'),
      ('💨', 'تهوية المكان قبل إعادة التشغيل', 'Ventilate before the area reopens'),
    ],
    checklist: [
      ('مسح أسطح التلامس: المقابض والأزرار والحواف', 'Wipe handles, buttons and rails'),
      ('ترك المطهّر لزمن التلامس المطلوب', 'Leave the product for its contact time'),
      ('تعقيم الأجهزة الطبية غير الحرجة', 'Disinfect non-critical equipment'),
      ('تغيير المنشفة بين كل غرفة وأخرى', 'A fresh cloth between rooms'),
      ('تسجيل المطهّر المستخدم وتركيزه', 'Record the product and its dilution'),
    ],
  );

  static const pool = ServiceSpec(
    code: 'pool',
    ar: 'صيانة المسابح', en: 'Pool maintenance',
    icon: '🏊', color: Color(0xFF0891B2),
    tagline: ('قراءات كيمياء المياه يوميًا — والمسبح يُغلق فور خروجها عن النطاق الآمن',
        'Daily water chemistry — the pool closes the moment it leaves the safe band'),
    facts: [
      ('🧪', 'الكلور الحر: ١–٣ جزء بالمليون', 'Free chlorine: 1–3 ppm'),
      ('⚗️', 'الأس الهيدروجيني: ٧.٢–٧.٨', 'pH: 7.2–7.8'),
      ('🌡️', 'حرارة الماء: ٢٦–٢٩ °م', 'Water temperature: 26–29 °C'),
      ('💧', 'العكارة أقل من ٠.٥ NTU', 'Turbidity below 0.5 NTU'),
    ],
    checklist: [
      ('قياس الكلور والأس الهيدروجيني وتسجيلهما', 'Measure and log chlorine and pH'),
      ('كشط السطح وتفريغ السلال', 'Skim the surface, empty the baskets'),
      ('غسيل عكسي للفلتر عند ارتفاع الضغط', 'Backwash the filter when pressure rises'),
      ('كنس القاع وتنظيف خط الماء', 'Vacuum the floor, scrub the waterline'),
      ('فحص المضخة والبحث عن تسريبات', 'Check the pump, look for leaks'),
    ],
  );

  static const watertank = ServiceSpec(
    code: 'watertank',
    ar: 'تنظيف خزانات المياه', en: 'Water tank cleaning',
    icon: '🚰', color: Color(0xFF0E7A5F),
    tagline: ('دورة تنظيف موثّقة كل ٦ أشهر، بشهادة وتحليل مخبري',
        'A documented six-monthly cycle, with a certificate and a lab test'),
    facts: [
      ('📆', 'دورة التنظيف كل ٦ أشهر', 'Cleaning cycle every six months'),
      ('🧫', 'عيّنة مخبرية بعد كل تنظيف', 'A lab sample after every clean'),
      ('🧯', 'تعقيم بالكلور المخفّف ثم شطف كامل', 'Chlorine disinfection, then a full rinse'),
      ('📄', 'شهادة تنظيف تُسلَّم للعميل', 'A cleaning certificate for the client'),
    ],
    checklist: [
      ('تفريغ الخزان وعزل خط التغذية', 'Drain the tank, isolate the feed'),
      ('إزالة الرواسب وتنظيف الجدران والقاع', 'Remove sediment, scrub walls and floor'),
      ('تعقيم بالكلور المخفّف', 'Disinfect with diluted chlorine'),
      ('شطف كامل حتى يزول أثر الكلور', 'Rinse until the chlorine clears'),
      ('أخذ عيّنة وإصدار الشهادة', 'Take a sample, issue the certificate'),
    ],
  );

  static ServiceSpec? byCode(String c) => {
        'pest': pest, 'disinfection': disinfection,
        'pool': pool, 'watertank': watertank,
      }[c];
}

/// A per-service client console: what was done, what is late, what is due, and
/// what the service is contractually supposed to deliver.
class SpecialtyServiceScreen extends StatefulWidget {
  const SpecialtyServiceScreen({super.key, required this.spec});
  final ServiceSpec spec;
  @override
  State<SpecialtyServiceScreen> createState() => _SpecialtyServiceScreenState();
}

class _SpecialtyServiceScreenState extends State<SpecialtyServiceScreen> {
  Map<String, dynamic>? _d;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.clientServiceBoard(widget.spec.code);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.spec;
    final stats = (_d?['stats'] as Map?) ?? const {};
    var recs = ((_d?['records'] as List?) ?? const []).cast<Map>();
    if (_filter == 'open') {
      recs = recs.where((w) => !['done', 'verified', 'cancelled'].contains(w['state'])).toList();
    } else if (_filter == 'overdue') {
      recs = recs.where((w) => w['is_overdue'] == true).toList();
    } else if (_filter == 'done') {
      recs = recs.where((w) => ['done', 'verified'].contains(w['state'])).toList();
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: s.color, foregroundColor: Colors.white,
        title: Text(tr(s.ar, s.en), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: s.color,
        onPressed: () => Navigator.push(context,
            MaterialPageRoute(builder: (_) => const RequestsScreen())),
        icon: const Icon(Icons.add_task_rounded),
        label: Text(tr('طلب خدمة', 'Request'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: _d == null
          ? Center(child: CircularProgressIndicator(color: s.color))
          : RefreshIndicator(
              color: s.color,
              onRefresh: _load,
              child: ListView(padding: EdgeInsets.zero, children: [
                _header(stats),
                _standards(),
                _filters(stats),
                if (recs.isEmpty) _empty(),
                for (final w in recs.take(120)) _woCard(w),
                _checklist(),
                const SizedBox(height: 90),
              ]),
            ),
    );
  }

  Widget _header(Map stats) {
    final s = widget.spec;
    final rate = ((stats['completion_rate'] as num?) ?? 0).toDouble();
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [s.color, _navy],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(22)),
        ),
        child: Column(children: [
          Row(children: [
            Text(s.icon, style: const TextStyle(fontSize: 30)),
            const SizedBox(width: 11),
            Expanded(child: Text(tr(s.tagline.$1, s.tagline.$2),
                style: const TextStyle(color: Colors.white, fontSize: 12.5,
                    fontWeight: FontWeight.w700, height: 1.35))),
          ]),
          const SizedBox(height: 14),
          Row(children: [
            _hs('${stats['total'] ?? 0}', tr('إجمالي الأعمال', 'Total')),
            _hd(),
            _hs('${stats['open'] ?? 0}', tr('مفتوحة', 'Open')),
            _hd(),
            _hs('${stats['overdue'] ?? 0}', tr('متأخرة', 'Overdue')),
            _hd(),
            _hs('${rate.toStringAsFixed(0)}%', tr('الإنجاز', 'Completion')),
          ]),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: (rate / 100).clamp(0.0, 1.0), minHeight: 7,
              backgroundColor: Colors.white.withValues(alpha: 0.22),
              valueColor: AlwaysStoppedAnimation(
                  rate >= 85 ? const Color(0xFF37C98A) : const Color(0xFFF5B638)),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _hs(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.85),
                fontSize: 9.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.2));

  Widget _standards() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 16, 12, 0),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('معايير الخدمة', 'Service standards'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
          const SizedBox(height: 9),
          GridView.count(
            crossAxisCount: 2, shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 9, mainAxisSpacing: 9, childAspectRatio: 2.4,
            children: [
              for (final f in widget.spec.facts)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
                  decoration: BoxDecoration(color: Colors.white,
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(color: Colors.grey.shade200)),
                  child: Row(children: [
                    Text(f.$1, style: const TextStyle(fontSize: 17)),
                    const SizedBox(width: 8),
                    Expanded(child: Text(tr(f.$2, f.$3), maxLines: 3,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, height: 1.3))),
                  ]),
                ),
            ],
          ),
        ]),
      );

  Widget _filters(Map stats) {
    final s = widget.spec;
    final opts = [
      ('all', tr('الكل', 'All'), '${stats['total'] ?? 0}'),
      ('open', tr('مفتوحة', 'Open'), '${stats['open'] ?? 0}'),
      ('overdue', tr('متأخرة', 'Overdue'), '${stats['overdue'] ?? 0}'),
      ('done', tr('منجزة', 'Done'), '${stats['done'] ?? 0}'),
    ];
    return SizedBox(
      height: 46,
      child: ListView(scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(10, 12, 10, 0), children: [
        for (final o in opts)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: ChoiceChip(
              selected: _filter == o.$1,
              label: Text('${o.$2} (${o.$3})',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5,
                      color: _filter == o.$1 ? Colors.white : _navy)),
              selectedColor: s.color, backgroundColor: Colors.white,
              side: BorderSide(color: _filter == o.$1 ? s.color : Colors.grey.shade300),
              onSelected: (_) => setState(() => _filter = o.$1),
            ),
          ),
      ]),
    );
  }

  Widget _woCard(Map w) {
    final overdue = w['is_overdue'] == true;
    final done = ['done', 'verified'].contains(w['state']);
    final c = done
        ? const Color(0xFF16A34A)
        : (overdue ? const Color(0xFFE11D48) : widget.spec.color);
    final photos = ((w['media_count'] as num?) ?? 0).toInt();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => WorkOrderDetailScreen(
                  id: (w['id'] as num).toInt(), title: '${w['title'] ?? ''}'))),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.grey.shade200)),
            child: Row(children: [
              Container(width: 5, height: 46,
                  decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${w['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
                const SizedBox(height: 3),
                Text([w['location'], w['employee']].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 5, children: [
                  _tag('${w['state_label'] ?? w['state']}', c),
                  if (overdue) _tag('⚠ ${tr('متأخر', 'Overdue')}', const Color(0xFFE11D48)),
                  if (photos > 0) _tag('📷 $photos', const Color(0xFF64748B)),
                  if (w['request_datetime'] != null)
                    _tag('${w['request_datetime']}'.split(' ').first, const Color(0xFF94A3B8)),
                ]),
              ])),
              Icon(Icons.chevron_left_rounded, color: Colors.grey.shade400),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _checklist() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 20, 12, 0),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(15),
              border: Border.all(color: Colors.grey.shade200)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('ماذا تشمل كل زيارة؟', 'What each visit covers'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
            const SizedBox(height: 10),
            for (final c in widget.spec.checklist)
              Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(Icons.check_circle_rounded, size: 17, color: widget.spec.color),
                  const SizedBox(width: 9),
                  Expanded(child: Text(tr(c.$1, c.$2),
                      style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, height: 1.35))),
                ]),
              ),
          ]),
        ),
      );

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.11),
            borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  Widget _empty() => Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: Column(children: [
          Text(widget.spec.icon, style: const TextStyle(fontSize: 44)),
          const SizedBox(height: 8),
          Text(tr('لا أعمال في هذا التصنيف', 'Nothing in this filter'),
              style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ]),
      );
}
