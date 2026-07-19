import 'dart:async';
import 'package:flutter/material.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

const _navy = Color(0xFF0E3A5F);
const _accent = Color(0xFF6D28D9);

/// برمجة شرائح NFC — the settings console for tagging locations: write the
/// location's code onto a blank tag, register the tag's hardware id against it,
/// verify any tag in the field, and manage the tag lifecycle
/// (مفعّلة / معطّلة / مفقودة).
class NfcProvisionScreen extends StatefulWidget {
  const NfcProvisionScreen({super.key});
  @override
  State<NfcProvisionScreen> createState() => _NfcProvisionScreenState();
}

class _NfcProvisionScreenState extends State<NfcProvisionScreen> {
  Map<String, dynamic>? _data;
  String _state = 'all';
  int? _facilityId;
  String _q = '';
  Timer? _debounce;
  bool _busy = false;

  static const _states = [
    ('all', 'الكل', 'All'),
    ('unprogrammed', 'غير مبرمَجة', 'Unprogrammed'),
    ('programmed', 'مبرمَجة', 'Programmed'),
    ('disabled', 'معطّلة', 'Disabled'),
  ];
  static const _stateColors = {
    'active': Color(0xFF16A34A), 'none': Color(0xFF94A3B8),
    'disabled': Color(0xFFF59E0B), 'lost': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    try { NfcManager.instance.stopSession(); } catch (_) {}
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api
          .nfcLocations(facilityId: _facilityId, state: _state, q: _q);
      if (mounted) setState(() => _data = d);
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  void _onSearch(String v) {
    _q = v;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _load);
  }

  void _snack(String m, {Color? c}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c ?? _accent, behavior: SnackBarBehavior.floating));

  // ---------------------------------------------------------------- NFC ----
  /// Read a tag: returns (uid, wroteOk). Writes the payload when the tag allows.
  Future<(String, bool)?> _tagSession({String? writePayload, required String prompt}) async {
    final available = await NfcManager.instance.isAvailable();
    if (!available) {
      _snack(tr('NFC غير متاح على هذا الجهاز', 'NFC is not available on this device'), c: const Color(0xFFE11D48));
      return null;
    }
    final completer = Completer<(String, bool)?>();
    if (!mounted) return null;
    showDialog(context: context, barrierDismissible: true, builder: (_) => AlertDialog(
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.nfc_rounded, size: 52, color: _accent),
        const SizedBox(height: 14),
        Text(prompt, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
        const SizedBox(height: 8),
        Text(tr('أبقِ الجهاز ملاصقًا للشريحة حتى تنتهي العملية',
                'Keep the phone on the tag until it finishes'),
            textAlign: TextAlign.center, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
      ]),
      actions: [TextButton(onPressed: () {
        try { NfcManager.instance.stopSession(); } catch (_) {}
        if (!completer.isCompleted) completer.complete(null);
        Navigator.pop(context);
      }, child: Text(tr('إلغاء', 'Cancel')))],
    )).then((_) {
      if (!completer.isCompleted) completer.complete(null);
    });

    NfcManager.instance.startSession(onDiscovered: (tag) async {
      String? uid;
      bool wrote = false;
      try {
        // the tag's hardware id — our reliable identifier even if it is locked
        for (final k in ['nfca', 'nfcb', 'nfcf', 'nfcv', 'mifareclassic', 'mifareultralight', 'iso7816']) {
          final ident = tag.data[k]?['identifier'] as List?;
          if (ident != null && ident.isNotEmpty) {
            uid = ident.map((b) => (b as int).toRadixString(16).padLeft(2, '0')).join().toUpperCase();
            break;
          }
        }
        // best-effort: write the location code so any reader shows it
        if (writePayload != null) {
          final ndef = Ndef.from(tag);
          if (ndef != null && ndef.isWritable) {
            await ndef.write(NdefMessage([NdefRecord.createText(writePayload)]));
            wrote = true;
          }
        }
      } catch (_) {}
      await NfcManager.instance.stopSession();
      if (!completer.isCompleted) completer.complete(uid == null ? null : (uid, wrote));
      if (mounted && Navigator.canPop(context)) Navigator.pop(context);
    });
    return completer.future;
  }

  /// Program (or re-program) one location's tag.
  Future<void> _program(Map loc, {bool force = false}) async {
    final res = await _tagSession(
      writePayload: '${loc['payload'] ?? loc['code']}',
      prompt: tr('قرّب الجهاز من الشريحة لبرمجة\n«${loc['name']}»',
                 'Hold the phone on the tag to program\n"${loc['name']}"'),
    );
    if (res == null) return;
    final (uid, wrote) = res;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api
          .nfcProvision(loc['id'] as int, uid, written: wrote, force: force);
      await _load();
      if (!mounted) return;
      setState(() => _busy = false);
      _snack(wrote
              ? tr('✅ بُرمجت الشريحة ورُبطت بالموقع', '✅ Tag written and paired')
              : tr('✅ رُبطت الشريحة (غير قابلة للكتابة — المعرّف كافٍ)',
                   '✅ Tag paired (locked tag — its id is enough)'),
          c: const Color(0xFF16A34A));
      _offerNext(loc);
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      final msg = '$e';
      // the tag already belongs to another location — offer to move it
      if (msg.contains(tr('مرتبطة بالفعل', 'Already bound')) || msg.contains('409')) {
        final move = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: Text(tr('الشريحة مستخدمة', 'Tag already in use')),
          content: Text(msg.replaceAll('Exception: ', '')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent),
                onPressed: () => Navigator.pop(c, true), child: Text(tr('نقلها لهذا الموقع', 'Move it here'))),
          ],
        ));
        if (move == true) await _program(loc, force: true);
      } else {
        _snack(msg);
      }
    }
  }

  /// After a successful write, offer the next unprogrammed location so a
  /// technician can tag a whole floor without going back to the list.
  void _offerNext(Map done) {
    final locs = ((_data?['locations'] as List?) ?? const []).cast<Map>();
    final next = locs.where((l) => l['id'] != done['id'] && l['nfc_state'] != 'active').toList();
    if (next.isEmpty) return;
    final n = next.first;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      duration: const Duration(seconds: 6),
      backgroundColor: _navy,
      content: Text(tr('التالي: ${n['name']}', 'Next: ${n['name']}')),
      action: SnackBarAction(
        label: tr('برمجة', 'Program'), textColor: Colors.white,
        onPressed: () => _program(n)),
    ));
  }

  /// Tap any tag and be told which location it resolves to.
  Future<void> _verify() async {
    final res = await _tagSession(prompt: tr('قرّب الجهاز من أي شريحة للتحقق منها',
                                             'Hold the phone on any tag to identify it'));
    if (res == null) return;
    final (uid, _) = res;
    try {
      final d = await context.read<AuthProvider>().api.nfcVerify(uid);
      if (!mounted) return;
      showDialog(context: context, builder: (_) => AlertDialog(
        title: Row(children: [
          Icon(d['known'] == true ? Icons.verified_rounded : Icons.help_outline_rounded,
              color: d['known'] == true ? const Color(0xFF16A34A) : const Color(0xFFE11D48)),
          const SizedBox(width: 8),
          Text(d['known'] == true ? tr('شريحة معروفة', 'Known tag') : tr('شريحة غير مسجّلة', 'Unregistered tag')),
        ]),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (d['known'] == true) ...[
            Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: _navy)),
            const SizedBox(height: 4),
            Text([d['facility'], d['building'], d['floor']].where((x) => x != null).join(' · '),
                style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600)),
            const SizedBox(height: 8),
            Text('${tr('الحالة', 'State')}: ${d['nfc_state_label']}',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
            if (d['nfc_written_by'] != null)
              Text('${tr('برمجها', 'Programmed by')}: ${d['nfc_written_by']} · ${d['nfc_written_on'] ?? ''}',
                  style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
          ] else
            Text(tr('هذه الشريحة غير مرتبطة بأي موقع — يمكنك برمجتها من القائمة.',
                    'This tag is not linked to any location — program it from the list.'),
                style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 10),
          SelectableText('UID: $uid', style: TextStyle(fontSize: 11, color: Colors.grey.shade500, fontFamily: 'monospace')),
        ]),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('حسناً', 'OK')))],
      ));
    } catch (e) {
      _snack('$e');
    }
  }

  Future<void> _lifecycle(Map loc, String action, String confirm) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('تأكيد', 'Confirm')),
      content: Text(confirm),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.nfcAction(loc['id'] as int, action);
      await _load();
      if (mounted) _snack(tr('تم التحديث', 'Updated'), c: const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  // --------------------------------------------------------------- build ---
  @override
  Widget build(BuildContext context) {
    final d = _data;
    final counts = (d?['counts'] as Map?) ?? const {};
    final canManage = d?['can_manage'] == true;
    final locs = ((d?['locations'] as List?) ?? const []).cast<Map>();
    final facilities = ((d?['facilities'] as List?) ?? const []).cast<Map>();
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('برمجة شرائح NFC', 'NFC tags'), style: const TextStyle(fontWeight: FontWeight.w900)),
        actions: [
          IconButton(icon: const Icon(Icons.travel_explore_rounded),
              tooltip: tr('اختبار شريحة', 'Identify a tag'), onPressed: _verify),
        ],
      ),
      body: d == null
          ? const Center(child: CircularProgressIndicator(color: _accent))
          : RefreshIndicator(
              color: _accent,
              onRefresh: _load,
              child: Column(children: [
                _header(counts, canManage),
                _filters(facilities),
                Expanded(child: locs.isEmpty
                    ? _empty()
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                        itemCount: locs.length,
                        itemBuilder: (_, i) => _locCard(locs[i], canManage),
                      )),
              ]),
            ),
    );
  }

  Widget _header(Map counts, bool canManage) => CustomPaint(
        painter: const BrandPattern(opacity: 0.07),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [_accent, Color(0xFF4C1D95)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(20)),
          ),
          child: Column(children: [
            Row(children: [
              _hStat('${counts['programmed'] ?? 0}', tr('مبرمَجة', 'Programmed')),
              _hDiv(),
              _hStat('${counts['unprogrammed'] ?? 0}', tr('غير مبرمَجة', 'Pending')),
              _hDiv(),
              _hStat('${counts['disabled'] ?? 0}', tr('معطّلة', 'Disabled')),
              _hDiv(),
              _hStat('${counts['total'] ?? 0}', tr('إجمالي المواقع', 'Locations')),
            ]),
            if (!canManage) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(12)),
                child: Text(tr('لديك صلاحية العرض فقط — البرمجة للمشرفين والمدراء',
                               'View only — programming is for supervisors and managers'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w700)),
              ),
            ],
          ]),
        ),
      );

  Widget _hStat(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _hDiv() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.2));

  Widget _filters(List<Map> facilities) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
          child: TextField(
            onChanged: _onSearch,
            decoration: InputDecoration(
              hintText: tr('ابحث بالموقع أو الرمز أو معرّف الشريحة…', 'Search location, code or tag id…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              filled: true, fillColor: Colors.white, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            ),
          ),
        ),
        SizedBox(height: 40, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final s in _states) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 2),
            child: ChoiceChip(
              selected: _state == s.$1,
              label: Text(tr(s.$2, s.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: _state == s.$1 ? Colors.white : _navy)),
              selectedColor: _accent, backgroundColor: Colors.white,
              side: BorderSide(color: _state == s.$1 ? _accent : Colors.grey.shade300),
              onSelected: (_) { setState(() => _state = s.$1); _load(); },
            ),
          ),
          if (facilities.length > 1)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 2),
              child: ChoiceChip(
                selected: _facilityId != null,
                avatar: const Icon(Icons.apartment_rounded, size: 15),
                label: Text(_facilityId == null
                        ? tr('كل المرافق', 'All facilities')
                        : '${facilities.firstWhere((f) => f['id'] == _facilityId, orElse: () => const {})['name'] ?? ''}',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: _facilityId != null ? Colors.white : _navy)),
                selectedColor: _navy, backgroundColor: Colors.white,
                side: BorderSide(color: _facilityId != null ? _navy : Colors.grey.shade300),
                onSelected: (_) => _pickFacility(facilities),
              ),
            ),
        ])),
      ]);

  Future<void> _pickFacility(List<Map> facilities) async {
    final id = await showModalBottomSheet<Object>(context: context, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => SafeArea(child: ListView(shrinkWrap: true, children: [
        ListTile(leading: const Icon(Icons.clear_all_rounded), title: Text(tr('كل المرافق', 'All facilities')),
            onTap: () => Navigator.pop(ctx, 'all')),
        for (final f in facilities)
          ListTile(leading: const Icon(Icons.apartment_rounded, color: _navy), title: Text('${f['name']}'),
              onTap: () => Navigator.pop(ctx, f['id'] as int)),
      ])));
    if (id == null) return;
    setState(() => _facilityId = id == 'all' ? null : id as int);
    _load();
  }

  Widget _locCard(Map l, bool canManage) {
    final st = '${l['nfc_state'] ?? 'none'}';
    final c = _stateColors[st] ?? Colors.grey;
    final active = st == 'active';
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(children: [
          Row(children: [
            Container(width: 42, height: 42, alignment: Alignment.center,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                child: Icon(active ? Icons.nfc_rounded : Icons.nfc_outlined, color: c, size: 21)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${l['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
              const SizedBox(height: 3),
              Text([l['facility'], l['building'], l['floor'], l['code']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
            ])),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.4))),
              child: Text('${l['nfc_state_label']}', style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w900)),
            ),
          ]),
          if (l['nfc_uid'] != null) ...[
            const SizedBox(height: 8),
            Row(children: [
              Icon(Icons.tag_rounded, size: 13, color: Colors.grey.shade500),
              const SizedBox(width: 5),
              Expanded(child: Text('${l['nfc_uid']}',
                  style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600, fontFamily: 'monospace'))),
              if (l['nfc_written_by'] != null)
                Text('${l['nfc_written_by']}', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
            ]),
          ],
          if (canManage) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: _accent, side: const BorderSide(color: _accent), minimumSize: const Size(0, 38)),
                onPressed: _busy ? null : () => _program(l),
                icon: Icon(active ? Icons.refresh_rounded : Icons.nfc_rounded, size: 17),
                label: Text(active ? tr('إعادة البرمجة', 'Re-program') : tr('برمجة الشريحة', 'Program tag'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
              )),
              if (l['nfc_uid'] != null) ...[
                const SizedBox(width: 8),
                IconButton(
                  tooltip: active ? tr('تعطيل', 'Disable') : tr('تفعيل', 'Enable'),
                  icon: Icon(active ? Icons.pause_circle_rounded : Icons.play_circle_rounded,
                      color: active ? const Color(0xFFF59E0B) : const Color(0xFF16A34A)),
                  onPressed: () => _lifecycle(l, active ? 'disable' : 'enable',
                      active ? tr('تعطيل شريحة هذا الموقع؟', 'Disable this location tag?')
                             : tr('إعادة تفعيل الشريحة؟', 'Re-enable the tag?')),
                ),
                IconButton(
                  tooltip: tr('إلغاء الربط (مفقودة)', 'Unpair (lost)'),
                  icon: const Icon(Icons.link_off_rounded, color: Color(0xFFE11D48)),
                  onPressed: () => _lifecycle(l, 'revoke',
                      tr('إلغاء ربط الشريحة؟ يمكنك بعدها برمجة شريحة جديدة.',
                         'Unpair the tag? You can then program a new one.')),
                ),
              ],
            ]),
          ],
        ]),
      ),
    );
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 90),
        Icon(Icons.nfc_outlined, size: 58, color: Colors.grey.shade300),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا مواقع مطابقة', 'No matching locations'),
            style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
      ]);
}
