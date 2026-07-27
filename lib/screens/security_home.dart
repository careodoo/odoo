import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'scan_screen.dart';
import 'workorders_screen.dart';
import 'security_incidents_screen.dart';
import 'security_list_screen.dart';
import 'security_section_screen.dart';
import 'security_my_team_screen.dart';
import 'security_tasks_screen.dart';
import 'security_patrol_points_screen.dart';
import 'security_my_profile_screen.dart';
import 'security_my_schedule_screen.dart';
import 'security_post_orders_screen.dart';
import 'security_handover_screen.dart';
import 'security_dar_screen.dart';
import 'security_gate_log_screen.dart';
import 'permits_screen.dart';
import 'security_keys_screen.dart';
import 'security_inspections_screen.dart';
import 'security_gatepasses_screen.dart';
import 'security_emergency_screen.dart';
import 'security_stream_screen.dart';
import 'live_stream_banner.dart';
import 'heartbeat_pinger.dart';
import 'security_patrols_screen.dart';
import 'security_patrol_log_screen.dart';
import 'supervisor_screen.dart';
import 'security_supervisor_screen.dart';
import 'stream_archive_screen.dart';
import 'shift_card.dart';

/// The security app's face — deliberately different: a dark "command centre"
/// look, large glanceable tiles, and a prominent panic action. This is the
/// screen the user asked to be "very, very professional".
class SecurityHome extends StatelessWidget {
  const SecurityHome({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(
        title: Text(tr('🛡️  مركز الأمن', '🛡️  Security centre')),
        actions: [
          const ShiftToggle(onSurface: true),
          NotifBell(unread: p.unreadNotifications),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthProvider>().logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), Color(0xFF0F172A)]),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Row(
              children: [
                const CircleAvatar(radius: 26, backgroundColor: Color(0xFFE5484D), child: Text('🛡️', style: TextStyle(fontSize: 24))),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p.name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                      Text(tr('حارس أمن · وردية نشطة', 'Security guard · on shift'), style: TextStyle(color: Color(0xFF9CB2CD), fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const _MyOverviewHeader(),
          const HeartbeatPinger(),
          const LiveStreamBanner(),
          MyStatsRow(counts: p.counts),
          const SizedBox(height: 14),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.05,
            children: [
              if (p.isSupervisor)
                _Tile(
                  icon: '🎖️', label: tr('أدوات المشرف', 'Supervisor tools'),
                  sub: tr('مهام · دوريات · تصاريح · حالة الفريق', 'Assign · patrols · team status'),
                  onTap: () => Navigator.push(context,
                      MaterialPageRoute(builder: (_) => const SecuritySupervisorScreen())),
                ),
              if (p.isSupervisor)
                _Tile(
                  icon: '🧭', label: 'لوحة المشرف',
                  sub: tr('إحصائيات · إسناد', 'Stats · assignment'),
                  onTap: () => Navigator.push(context,
                      MaterialPageRoute(builder: (_) => const SupervisorScreen())),
                ),
              _Tile(
                icon: '📍', label: tr('مسح نقطة دورية', 'Scan checkpoint'),
                sub: tr('إثبات تفتيش', 'Patrol proof'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ScanScreen())),
              ),
              _Tile(
                icon: '📋', label: tr('مهامي', 'My tasks'),
                sub: tr('أوامر العمل', 'Work orders'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WorkOrdersScreen())),
              ),
              _Tile(
                icon: '🚨', label: tr('زر الطوارئ', 'Panic'),
                sub: tr('بلاغ فوري بالبصمة', 'Biometric SOS'), danger: true,
                onTap: () => Emergency.raise(context),
              ),
              _Tile(
                icon: '🆘', label: tr('نداءات الاستغاثة', 'SOS alerts'),
                sub: tr('خريطة حيّة للفريق', 'Live team map'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityEmergencyMapScreen())),
              ),
              _Tile(
                icon: '🎥', label: tr('بث مباشر', 'Go live'),
                sub: tr('بث كاميرا للفريق', 'Broadcast to team'),
                onTap: () => Stream.goLive(context),
              ),
              _Tile(
                icon: '🎬', label: tr('سجل البثّ', 'Broadcasts archive'),
                sub: tr('التسجيلات وإعادة التشغيل', 'Recordings & replay'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const StreamArchiveScreen())),
              ),
              _Tile(
                icon: '📝', label: tr('البلاغات الأمنية', 'Incidents'),
                sub: tr('عرض · تسجيل حادث', 'View · report'),
                onTap: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const SecurityIncidentsScreen())),
              ),
              _Tile(
                icon: '🚶', label: tr('الدوريات', 'Patrols'),
                sub: tr('المسارات والحالة', 'Routes & status'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityPatrolsScreen())),
              ),
              _Tile(
                icon: '🗒️', label: tr('سجل الجولات', 'Patrol log'),
                sub: tr('المواعيد والإنجاز', 'Times & completion'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityPatrolLogScreen())),
              ),
              _Tile(
                icon: '🔑', label: tr('المفاتيح', 'Keys'),
                sub: tr('مسح وصرف وإرجاع', 'Scan · out · in'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityKeysScreen())),
              ),
              _Tile(
                icon: '🚪', label: tr('التصاريح', 'Permits'),
                sub: tr('إدخال وإخراج الأشخاص', 'People in/out'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const PermitsScreen())),
              ),
              _secTile(context, '👮', tr('الحرّاس', 'Guards'), tr('الحالة والموقع', 'Status & location'), 'guards'),
              _Tile(
                icon: '📖', label: tr('الأوامر الدائمة', 'Post orders'), sub: tr('تعليمات الموقع · إقرار', 'Site SOP · acknowledge'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityPostOrdersScreen()))),
              _Tile(
                icon: '🔄', label: tr('تسليم الوردية', 'Handover'), sub: tr('تسليم/استلام للحارس التالي', 'Hand over to next guard'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityHandoverScreen()))),
              _Tile(
                icon: '📝', label: tr('تقرير النشاط اليومي', 'Daily report'), sub: tr('نشاط اليوم · ملخّص الوردية', "Today's activity · summary"),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityDarScreen()))),
              _Tile(
                icon: '🚧', label: tr('سجل البوابة', 'Gate register'), sub: tr('زوّار ومركبات · دخول/خروج', 'Visitors & vehicles · in/out'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityGateLogScreen()))),
              _Tile(
                icon: '🪪', label: tr('ملفي المهني', 'My profile'), sub: tr('شهادات · مهارات · معدّات', 'Certs · skills · gear'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityMyProfileScreen()))),
              _Tile(
                icon: '👥', label: tr('فريقي', 'My team'), sub: tr('أعضاء فريقي وحالتهم', 'My team members'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityMyTeamScreen()))),
              _Tile(
                icon: '🗓️', label: tr('جدولي', 'My schedule'), sub: tr('ورديّاتي · حضور/انصراف', 'My shifts · in/out'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityMyScheduleScreen()))),
              _Tile(
                icon: '📍', label: tr('نقاط الدوريات', 'Patrol points'), sub: tr('حسب المرفق · إحصائيات', 'By facility · stats'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityPatrolPointsScreen()))),
              _secTile(context, '🧾', tr('سجلّات الدوريات', 'Patrol logs'), tr('المسح والوقت', 'Scans & time'), 'patrol_logs'),
              _Tile(
                icon: '🔎', label: tr('التفتيشات', 'Inspections'), sub: tr('فحص · إسناد · أمر عمل', 'Check · assign · WO'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityInspectionsScreen()))),
              _Tile(
                icon: '✅', label: tr('مهام الأمن', 'Security tasks'), sub: tr('مهامي · أرشيف · إجراءات', 'My tasks · archive · actions'),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityTasksScreen()))),
              _Tile(
                icon: '🔔', label: tr('اختبار الإشعارات', 'Test alerts'), sub: tr('جرّب كل نوع إشعار', 'Try each type'),
                onTap: () => _testNotifSheet(context)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _secTile(BuildContext c, String icon, String label, String sub, String kind) => _Tile(
        icon: icon, label: label, sub: sub,
        onTap: () => Navigator.push(c, MaterialPageRoute(
            builder: (_) => SecuritySectionScreen(kind: kind, title: label))),
      );

  /// ورقة اختبار الإشعارات: يرسل الخادم إشعاراً تجريبياً لكل نوع ليتأكد الحارس من
  /// وصولها (يشمل تنبيهاً إن كان الجهاز غير مسجّل — أي إذن الإشعارات مرفوض).
  void _testNotifSheet(BuildContext c) {
    const types = [
      ('info', '🔔', 'إشعار عام'),
      ('task', '📋', 'مهمة'),
      ('patrol', '🚶', 'دورية'),
      ('point', '📍', 'نقطة تفتيش'),
      ('incident', '⚠️', 'بلاغ أمني'),
      ('gatepass', '🚪', 'تصريح'),
      ('key', '🔑', 'عهدة مفاتيح'),
      ('stream', '🎥', 'بث مباشر'),
      ('alert', '🆘', 'استغاثة'),
      ('message', '💬', 'رسالة'),
    ];
    showModalBottomSheet(
      context: c, backgroundColor: const Color(0xFF152238), isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (sheetCtx) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFF34506F), borderRadius: BorderRadius.circular(3))),
          const SizedBox(height: 14),
          Text(tr('اختبار الإشعارات', 'Test notifications'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 4),
          Text(tr('اضغط أي نوع ليصلك إشعار تجريبي', 'Tap a type to receive a test alert'),
              style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
          const SizedBox(height: 14),
          Wrap(spacing: 9, runSpacing: 9, alignment: WrapAlignment.center, children: [
            for (final t in types)
              InkWell(
                onTap: () => _sendTest(sheetCtx, t.$1),
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  width: 96, padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(color: const Color(0xFF0F1B2E), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFF20344E))),
                  child: Column(children: [
                    Text(t.$2, style: const TextStyle(fontSize: 22)),
                    const SizedBox(height: 5),
                    Text(t.$3, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
                  ]),
                ),
              ),
          ]),
        ]),
      ),
    );
  }

  Future<void> _sendTest(BuildContext c, String type) async {
    final messenger = ScaffoldMessenger.of(c);
    try {
      final r = await c.read<AuthProvider>().api.securityNotifyTest(type);
      final hasDevice = r['has_device'] == true;
      messenger.showSnackBar(SnackBar(
        backgroundColor: hasDevice ? const Color(0xFF37C98A) : const Color(0xFFF7A23B),
        content: Text(hasDevice
            ? tr('أُرسل الإشعار — تحقّق من شريط الإشعارات', 'Sent — check your notification shade')
            : tr('جهازك غير مسجّل! فعّل إذن الإشعارات وأعد الدخول', 'Device not registered! enable notification permission & re-login')),
      ));
    } catch (e) {
      messenger.showSnackBar(SnackBar(backgroundColor: const Color(0xFFE5484D), content: Text('$e')));
    }
  }


}

/// ترويسة «نظرتي اليومية» — تجمع مؤشّرات كل ميزات الحارس (مهام/دوريات/أوامر/
/// تسليم/بوابة/تقرير اليوم) في شريط واحد قابل للمسح السريع مع تنبيهات ملوّنة.
class _MyOverviewHeader extends StatefulWidget {
  const _MyOverviewHeader();
  @override
  State<_MyOverviewHeader> createState() => _MyOverviewHeaderState();
}

class _MyOverviewHeaderState extends State<_MyOverviewHeader> {
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _blue = Color(0xFF4AA8FF);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _o;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try {
      final o = await context.read<AuthProvider>().api.securityMyOverview();
      if (mounted) setState(() { _o = o; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading || _o == null) return const SizedBox.shrink();
    final o = _o!;
    final darDone = (o['dar_done'] ?? false) as bool;
    final chips = <Widget>[
      _kpi('📋', '${o['tasks_open'] ?? 0}', tr('مهام مفتوحة', 'Open tasks'),
          (o['tasks_open'] ?? 0) > 0 ? _amber : _muted),
      _kpi('🚶', '${o['patrols_today'] ?? 0}', tr('دوريات اليوم', 'Patrols'), _green),
      _kpi('📖', '${o['post_orders_unacked'] ?? 0}', tr('أوامر غير مُقرّة', 'Unacked SOP'),
          (o['post_orders_unacked'] ?? 0) > 0 ? _red : _muted),
      _kpi('🔄', '${o['handovers_pending'] ?? 0}', tr('تسليم بانتظارك', 'Handovers'),
          (o['handovers_pending'] ?? 0) > 0 ? _amber : _muted),
      _kpi('🚧', '${o['gate_inside'] ?? 0}', tr('بالداخل الآن', 'Inside now'), _blue),
      _kpi(darDone ? '✅' : '📝', darDone ? tr('تمّ', 'Done') : tr('مطلوب', 'Due'),
          tr('تقرير اليوم', 'Daily report'), darDone ? _green : _amber),
      if ((o['certs_expiring'] ?? 0) > 0)
        _kpi('⏰', '${o['certs_expiring']}', tr('شهادات تنتهي', 'Certs expiring'), _red),
    ];
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Text('📊  ', style: TextStyle(fontSize: 14)),
          Text(tr('نظرتي اليومية', 'My day at a glance'),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
          const Spacer(),
          GestureDetector(onTap: () { setState(() => _loading = true); _load(); },
              child: const Icon(Icons.refresh_rounded, color: _muted, size: 18)),
        ]),
        const SizedBox(height: 10),
        SizedBox(
          height: 74,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: chips.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (_, i) => chips[i],
          ),
        ),
      ]),
    );
  }

  Widget _kpi(String emoji, String value, String label, Color c) => Container(
        width: 96,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12),
          border: Border.all(color: c.withValues(alpha: 0.30)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Row(children: [
            Text(emoji, style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 4),
            Text(value, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 17)),
          ]),
          const SizedBox(height: 3),
          Text(label, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: _muted, fontSize: 10.5, height: 1.1)),
        ]),
      );
}

class _Tile extends StatelessWidget {
  const _Tile({required this.icon, required this.label, required this.sub, required this.onTap, this.danger = false});
  final String icon;
  final String label;
  final String sub;
  final VoidCallback onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: danger ? const Color(0xFF3A1418) : const Color(0xFF152238),
          border: Border.all(color: danger ? const Color(0xFFE5484D) : const Color(0xFF294059)),
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(icon, style: const TextStyle(fontSize: 34)),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
            Text(sub, style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
