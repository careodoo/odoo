import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Treatment-center receiver workspace — the person at the processing center
/// records the actual received quantities/types, uploads photos & videos, and
/// confirms completion of the waste operation.
class ReceiverWasteScreen extends StatefulWidget {
  const ReceiverWasteScreen({super.key});
  @override
  State<ReceiverWasteScreen> createState() => _ReceiverWasteScreenState();
}

class _ReceiverWasteScreenState extends State<ReceiverWasteScreen> {
  static const _navy = Color(0xFF0E3A5F);
  static const _green = Color(0xFF16A34A);
  Future<List<dynamic>>? _orders;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _orders = context.read<AuthProvider>().api.wasteReceiverOrders());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F6F5),
      appBar: AppBar(backgroundColor: _navy, foregroundColor: Colors.white, title: Text(tr('استلام بالمركز', 'Center intake')), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _orders,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final orders = snap.data!;
            if (orders.isEmpty) {
              return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90), child: Column(children: [
                const Icon(Icons.factory_outlined, size: 60, color: Colors.grey),
                const SizedBox(height: 10),
                Text(tr('لا شحنات واردة للاستلام حاليًا', 'No incoming shipments'), style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w700)),
              ]))]);
            }
            return ListView.builder(padding: const EdgeInsets.all(12), itemCount: orders.length, itemBuilder: (_, i) => _card(orders[i] as Map));
          },
        ),
      ),
    );
  }

  Widget _card(Map o) => Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Text('♻️', style: TextStyle(fontSize: 20)), const SizedBox(width: 8),
            Expanded(child: Text('${o['serial']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy))),
            Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4), decoration: BoxDecoration(color: _navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(20)), child: Text('${o['state_label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: _navy))),
          ]),
          const SizedBox(height: 6),
          Text('${o['project'] ?? ''} · ${o['pickup'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 10),
          SizedBox(width: double.infinity, height: 46, child: ElevatedButton.icon(
            onPressed: () => _openIntake(o),
            icon: const Icon(Icons.fact_check_outlined),
            label: Text(tr('تسجيل الاستلام والتأكيد', 'Record intake & confirm'), style: const TextStyle(fontWeight: FontWeight.w800)),
            style: ElevatedButton.styleFrom(backgroundColor: _green, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          )),
        ]),
      );

  void _openIntake(Map o) {
    final weight = TextEditingController(text: '${o['final_weight'] ?? ''}');
    final note = TextEditingController(text: '${o['final_note'] ?? ''}');
    final items = <Map<String, dynamic>>[for (final i in (o['items'] as List? ?? [])) {'item_id': i['item_id'], 'item': i['item'], 'qty': (i['qty'] ?? 0).toString()}];
    final media = <Map<String, String>>[]; // {name, mimetype, data}
    bool busy = false;

    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) {
        Future<void> pick(ImageSource src, {bool video = false}) async {
          final x = video
              ? await ImagePicker().pickVideo(source: src)
              : await ImagePicker().pickImage(source: src, imageQuality: 70, maxWidth: 1600);
          if (x == null) return;
          final bytes = await File(x.path).readAsBytes();
          setSt(() => media.add({'name': x.name, 'mimetype': video ? 'video/mp4' : 'image/jpeg', 'data': base64Encode(bytes)}));
        }

        Future<void> submit(String confirm) async {
          setSt(() => busy = true);
          try {
            await context.read<AuthProvider>().api.wasteOrderReceive(o['id'] as int, {
              'final_weight': double.tryParse(weight.text) ?? 0,
              'final_note': note.text,
              'items': [for (final it in items) {'item_id': it['item_id'], 'quantity': double.tryParse('${it['qty']}') ?? 0}].where((e) => e['item_id'] != null).toList(),
              'media': media,
              'confirm': confirm,
            });
            if (ctx.mounted) Navigator.pop(ctx);
            if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم تسجيل الاستلام', 'Intake saved')), backgroundColor: _green)); _load(); }
          } catch (e) {
            setSt(() => busy = false);
            if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
          }
        }

        return DraggableScrollableSheet(
          expand: false, initialChildSize: 0.9, maxChildSize: 0.96,
          builder: (_, ctrl) => Container(
            decoration: const BoxDecoration(color: Color(0xFFF4F7FB), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: ListView(controller: ctrl, padding: const EdgeInsets.all(16), children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(3)))),
              const SizedBox(height: 12),
              Text('${tr('استلام الطلب', 'Receive order')} ${o['serial']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: _navy)),
              const SizedBox(height: 14),
              _sec(tr('الوزن النهائي المستلم (كجم)', 'Final received weight (kg)')),
              TextField(controller: weight, keyboardType: TextInputType.number, decoration: _dec(Icons.scale_outlined)),
              const SizedBox(height: 14),
              _sec(tr('الأصناف والكميات', 'Types & quantities')),
              for (int i = 0; i < items.length; i++) Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
                Expanded(flex: 2, child: Text('${items[i]['item'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600))),
                SizedBox(width: 90, child: TextField(
                  controller: TextEditingController(text: '${items[i]['qty']}'),
                  keyboardType: TextInputType.number, textAlign: TextAlign.center,
                  onChanged: (v) => items[i]['qty'] = v,
                  decoration: const InputDecoration(isDense: true, border: OutlineInputBorder(), hintText: 'الكمية'))),
              ])),
              const SizedBox(height: 6),
              _sec(tr('صور وفيديوهات الإثبات', 'Proof photos & videos')),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (int i = 0; i < media.length; i++) Chip(label: Text(media[i]['mimetype']!.startsWith('video') ? '🎬 ${i + 1}' : '📷 ${i + 1}'), onDeleted: () => setSt(() => media.removeAt(i))),
                ActionChip(avatar: const Icon(Icons.photo_camera, size: 18), label: Text(tr('كاميرا', 'Camera')), onPressed: () => pick(ImageSource.camera)),
                ActionChip(avatar: const Icon(Icons.photo_library, size: 18), label: Text(tr('صورة', 'Photo')), onPressed: () => pick(ImageSource.gallery)),
                ActionChip(avatar: const Icon(Icons.videocam, size: 18), label: Text(tr('فيديو', 'Video')), onPressed: () => pick(ImageSource.gallery, video: true)),
              ]),
              const SizedBox(height: 14),
              _sec(tr('ملاحظة الاستلام', 'Intake note')),
              TextField(controller: note, maxLines: 2, decoration: _dec(Icons.sticky_note_2_outlined)),
              const SizedBox(height: 18),
              if (busy) const Center(child: CircularProgressIndicator()) else Column(children: [
                SizedBox(width: double.infinity, height: 50, child: ElevatedButton.icon(
                  onPressed: () => submit('completed'), icon: const Icon(Icons.verified_rounded),
                  label: Text(tr('تأكيد إتمام المعالجة', 'Confirm completion'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  style: ElevatedButton.styleFrom(backgroundColor: _green, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))))),
                const SizedBox(height: 8),
                SizedBox(width: double.infinity, height: 46, child: OutlinedButton(
                  onPressed: () => submit(''),
                  child: Text(tr('حفظ فقط (دون تأكيد)', 'Save only'), style: const TextStyle(fontWeight: FontWeight.w700)))),
              ]),
              const SizedBox(height: 20),
            ]),
          ),
        );
      }),
    );
  }

  Widget _sec(String t) => Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, color: _navy, fontSize: 14)));
  InputDecoration _dec(IconData ic) => InputDecoration(prefixIcon: Icon(ic, size: 20, color: _green), filled: true, fillColor: Colors.white, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none));
}
