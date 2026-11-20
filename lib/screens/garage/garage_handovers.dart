import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_home.dart' show kGrgNavy, kGrgBg, kGrgInk, kGrgGrey, kGrgGold;

Color _hoColor(String s) {
  switch (s) {
    case 'draft':
      return const Color(0xFF94A3B8);
    case 'submitted':
      return const Color(0xFF2563EB);
    case 'approved':
      return const Color(0xFF16A34A);
    case 'rejected':
      return const Color(0xFFDC3030);
    default:
      return kGrgGrey;
  }
}

/// D6 — محاضر استلام السيارات: قائمة + إنشاء (صور 4 جوانب إلزامية) + اعتماد مدير الفليت.
class GarageHandoversScreen extends StatefulWidget {
  const GarageHandoversScreen({super.key});
  @override
  State<GarageHandoversScreen> createState() => _GarageHandoversScreenState();
}

class _GarageHandoversScreenState extends State<GarageHandoversScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;
  String _state = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.grgHandovers(state: _state == 'all' ? null : _state);
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('استلام السيارات', 'Vehicle handovers')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: kGrgGold,
        foregroundColor: kGrgNavy,
        icon: const Icon(Icons.add_rounded),
        label: Text(tr('محضر جديد', 'New')),
        onPressed: _openCreate,
      ),
      body: Column(children: [
        _filters(),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا توجد محاضر', 'No handovers'), style: const TextStyle(color: kGrgGrey)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 90),
                        itemCount: _rows.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _card(_rows[i] as Map),
                      ),
                    ),
        ),
      ]),
    );
  }

  Widget _filters() {
    final opts = {'all': tr('الكل', 'All'), 'submitted': tr('بانتظار الاعتماد', 'Pending'), 'approved': tr('معتمدة', 'Approved')};
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
      child: Row(
        children: opts.entries.map((e) {
          final sel = _state == e.key;
          return Padding(
            padding: const EdgeInsets.only(left: 8),
            child: ChoiceChip(
              label: Text(e.value),
              selected: sel,
              selectedColor: kGrgNavy,
              labelStyle: TextStyle(color: sel ? Colors.white : kGrgInk, fontWeight: FontWeight.w700),
              onSelected: (_) {
                setState(() => _state = e.key);
                _load();
              },
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _card(Map h) {
    final st = (h['state'] ?? '').toString();
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        onTap: () => _openDetail((h['id'] as num).toInt()),
        leading: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(color: _hoColor(st).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(11)),
          child: const Icon(Icons.car_rental_rounded, color: kGrgNavy),
        ),
        title: Text('${h['name']} · ${h['vehicle']}', style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk)),
        subtitle: Text('${tr('إلى', 'To')}: ${h['to_driver'] ?? '—'}  ·  ${h['date'] ?? ''}',
            style: const TextStyle(color: kGrgGrey, fontSize: 12)),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
          decoration: BoxDecoration(color: _hoColor(st).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(20)),
          child: Text((h['state_label'] ?? '').toString(),
              style: TextStyle(color: _hoColor(st), fontWeight: FontWeight.w800, fontSize: 11)),
        ),
      ),
    );
  }

  Future<void> _openDetail(int id) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => _HandoverDetail(id: id)));
    _load();
  }

  Future<void> _openCreate() async {
    final ok = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const _HandoverCreate()));
    if (ok == true) _load();
  }
}

// ============ التفاصيل + الاعتماد ============
class _HandoverDetail extends StatefulWidget {
  final int id;
  const _HandoverDetail({required this.id});
  @override
  State<_HandoverDetail> createState() => _HandoverDetailState();
}

class _HandoverDetailState extends State<_HandoverDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _d;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _api.grgHandover(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  Future<void> _act(String action) async {
    setState(() => _busy = true);
    try {
      await _api.grgHandoverAction(widget.id, action);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تمّ', 'Done'))));
        await _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFDC3030)));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text(tr('محضر استلام', 'Handover'))),
      bottomNavigationBar: (d != null && d['state'] == 'submitted')
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
                      onPressed: _busy ? null : () => _act('approve'),
                      icon: const Icon(Icons.verified_rounded),
                      label: Text(tr('اعتماد (مدير الفليت)', 'Approve')),
                    ),
                  ),
                  const SizedBox(width: 10),
                  OutlinedButton(onPressed: _busy ? null : () => _act('reject'), child: Text(tr('رفض', 'Reject'))),
                ]),
              ),
            )
          : null,
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              _hdr(d),
              _sec(tr('المركبة', 'Vehicle'), [
                _kv(tr('المركبة', 'Vehicle'), d['vehicle']),
                _kv(tr('اللوحة', 'Plate'), d['plate']),
                _kv(tr('العداد', 'Odometer'), '${d['odometer']}'),
                _kv(tr('الوقود', 'Fuel'), d['fuel']),
              ]),
              _sec(tr('السائقان', 'Drivers'), [
                _kv(tr('المسلِّم', 'From'), d['from_driver']),
                _kv(tr('المستلم', 'To'), d['to_driver']),
              ]),
              _photos(d['has_photos'] as Map? ?? {}),
              _contents(d['contents'] as Map? ?? {}),
              if ((d['notes'] ?? '').toString().isNotEmpty) _sec(tr('ملاحظات', 'Notes'), [Text(d['notes'].toString())]),
            ]),
    );
  }

  Widget _hdr(Map d) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [kGrgNavy, Color(0xFF14306B)]), borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(d['name'].toString(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
              const SizedBox(height: 4),
              Text(d['date'].toString(), style: const TextStyle(color: Colors.white70)),
            ]),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
            child: Text((d['state_label'] ?? '').toString(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
          ),
        ]),
      );

  Widget _sec(String t, List<Widget> rows) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy)),
          const Divider(),
          ...rows,
        ]),
      );

  Widget _kv(String k, dynamic v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Expanded(flex: 2, child: Text(k, style: const TextStyle(color: kGrgGrey))),
          Expanded(flex: 3, child: Text((v ?? '—').toString(), style: const TextStyle(fontWeight: FontWeight.w700, color: kGrgInk))),
        ]),
      );

  Widget _photos(Map p) {
    final sides = {'front': tr('الأمام', 'Front'), 'back': tr('الخلف', 'Back'), 'left': tr('الأيسر', 'Left'), 'right': tr('الأيمن', 'Right')};
    return _sec(tr('صور الجوانب', 'Photos'), [
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: sides.entries.map((e) {
          final has = p[e.key] == true;
          return Container(
            width: 74,
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
                color: has ? const Color(0xFF16A34A).withValues(alpha: 0.1) : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(10)),
            child: Column(children: [
              Icon(has ? Icons.check_circle_rounded : Icons.image_not_supported_rounded,
                  color: has ? const Color(0xFF16A34A) : kGrgGrey),
              const SizedBox(height: 3),
              Text(e.value, style: const TextStyle(fontSize: 11, color: kGrgInk)),
            ]),
          );
        }).toList(),
      ),
    ]);
  }

  Widget _contents(Map c) {
    const labels = {
      'has_book': 'دفتر المركبة', 'has_extinguisher': 'طفاية', 'has_spare_tire': 'إطار احتياطي',
      'has_tool_kit': 'طقم عدّة', 'has_jack': 'جاك', 'has_first_aid': 'إسعافات',
      'has_plates': 'لوحات', 'has_cassette': 'كاسيت', 'has_curtains': 'ستائر',
      'has_wipers': 'مساحات', 'has_tarpaulin': 'توربال', 'has_top_lights': 'فنارات', 'has_reflective_triangle': 'مثلث عاكس',
    };
    return _sec(tr('المحتويات', 'Contents'), [
      Wrap(
        spacing: 6,
        runSpacing: 6,
        children: labels.entries.where((e) => c[e.key] == true).map((e) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: kGrgNavy.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(16)),
            child: Text('✓ ${e.value}', style: const TextStyle(fontSize: 12, color: kGrgInk)),
          );
        }).toList(),
      ),
    ]);
  }
}

// ============ الإنشاء ============
class _HandoverCreate extends StatefulWidget {
  const _HandoverCreate();
  @override
  State<_HandoverCreate> createState() => _HandoverCreateState();
}

class _HandoverCreateState extends State<_HandoverCreate> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _meta;
  int? _vehicleId, _fromId, _toId;
  final _odo = TextEditingController();
  final _notes = TextEditingController();
  final Map<String, String> _photos = {}; // side -> base64
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadMeta();
  }

  Future<void> _loadMeta() async {
    try {
      final m = await _api.grgHandoverMeta();
      if (mounted) setState(() => _meta = m);
    } catch (_) {}
  }

  Future<void> _pick(String side) async {
    final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 60, maxWidth: 1600);
    if (x == null) return;
    final b = await x.readAsBytes();
    setState(() => _photos[side] = base64Encode(b));
  }

  Future<void> _save() async {
    if (_vehicleId == null || _toId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر المركبة والسائق المستلم', 'Select vehicle & receiver'))));
      return;
    }
    if (_photos.length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('صور الجوانب الأربعة إلزامية', '4 photos required'))));
      return;
    }
    setState(() => _busy = true);
    try {
      await _api.grgHandoverCreate({
        'vehicle_id': _vehicleId,
        'to_driver_id': _toId,
        if (_fromId != null) 'from_driver_id': _fromId,
        if (_odo.text.isNotEmpty) 'odometer': _odo.text,
        if (_notes.text.isNotEmpty) 'notes': _notes.text,
        'photo_front': _photos['front'],
        'photo_back': _photos['back'],
        'photo_left': _photos['left'],
        'photo_right': _photos['right'],
        'submit': true,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تمّ إنشاء المحضر وتقديمه', 'Submitted'))));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFDC3030)));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final m = _meta;
    final vehicles = (m?['vehicles'] as List?) ?? [];
    final drivers = (m?['drivers'] as List?) ?? [];
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text(tr('محضر استلام جديد', 'New handover'))),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: kGrgGold, foregroundColor: kGrgNavy, minimumSize: const Size.fromHeight(50)),
            onPressed: _busy ? null : _save,
            icon: const Icon(Icons.send_rounded),
            label: Text(tr('حفظ وتقديم', 'Save & submit')),
          ),
        ),
      ),
      body: m == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              _dropdown(tr('المركبة *', 'Vehicle *'), vehicles, _vehicleId, (v) => setState(() => _vehicleId = v)),
              const SizedBox(height: 12),
              _dropdown(tr('السائق المسلِّم', 'From driver'), drivers, _fromId, (v) => setState(() => _fromId = v)),
              const SizedBox(height: 12),
              _dropdown(tr('السائق المستلم *', 'Receiver *'), drivers, _toId, (v) => setState(() => _toId = v)),
              const SizedBox(height: 12),
              TextField(controller: _odo, keyboardType: TextInputType.number, decoration: _dec(tr('قراءة العداد', 'Odometer'))),
              const SizedBox(height: 12),
              Text(tr('صور الجوانب الأربعة (إلزامية)', '4-side photos (required)'),
                  style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy)),
              const SizedBox(height: 8),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 1.3,
                children: [
                  _photoTile('front', tr('الأمام', 'Front')),
                  _photoTile('back', tr('الخلف', 'Back')),
                  _photoTile('left', tr('الأيسر', 'Left')),
                  _photoTile('right', tr('الأيمن', 'Right')),
                ],
              ),
              const SizedBox(height: 12),
              TextField(controller: _notes, maxLines: 3, decoration: _dec(tr('ملاحظات', 'Notes'))),
            ]),
    );
  }

  InputDecoration _dec(String h) => InputDecoration(
      labelText: h, filled: true, fillColor: Colors.white, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)));

  Widget _dropdown(String label, List opts, int? val, ValueChanged<int?> onCh) {
    return DropdownButtonFormField<int>(
      value: val,
      isExpanded: true,
      decoration: _dec(label),
      items: opts.map((o) {
        final mm = o as Map;
        return DropdownMenuItem<int>(value: (mm['id'] as num).toInt(), child: Text(mm['name'].toString(), overflow: TextOverflow.ellipsis));
      }).toList(),
      onChanged: onCh,
    );
  }

  Widget _photoTile(String side, String label) {
    final b64 = _photos[side];
    return InkWell(
      onTap: () => _pick(side),
      child: Container(
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: b64 != null ? const Color(0xFF16A34A) : const Color(0xFFCBD5E1), width: 1.5)),
        clipBehavior: Clip.antiAlias,
        child: b64 != null
            ? Stack(fit: StackFit.expand, children: [
                Image.memory(base64Decode(b64), fit: BoxFit.cover),
                Positioned(
                    bottom: 4,
                    right: 4,
                    child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        color: Colors.black54,
                        child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 11)))),
              ])
            : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.add_a_photo_rounded, color: kGrgGrey),
                const SizedBox(height: 4),
                Text(label, style: const TextStyle(color: kGrgInk, fontWeight: FontWeight.w700)),
              ]),
      ),
    );
  }
}
