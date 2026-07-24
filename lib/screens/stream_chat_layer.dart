import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// طبقة الدردشة الحيّة على البثّ: تعرض الرسائل المنسابة أسفل البثّ وحقل إدخال،
/// وتستطلع الرسائل الجديدة دورياً. تُستخدم في شاشتي الحارس والعميل معاً.
class StreamChatLayer extends StatefulWidget {
  final int incidentId;
  final bool isClient;
  final bool compact; // في شاشة الحارس نعرض ارتفاعاً أقل
  const StreamChatLayer({super.key, required this.incidentId, this.isClient = false, this.compact = false});

  @override
  State<StreamChatLayer> createState() => _StreamChatLayerState();
}

class _StreamChatLayerState extends State<StreamChatLayer> {
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);

  final _ctl = TextEditingController();
  final _scroll = ScrollController();
  final List<Map> _msgs = [];
  Timer? _poll;
  int _lastId = 0;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _tick();
    _poll = Timer.periodic(const Duration(seconds: 3), (_) => _tick());
  }

  Future<void> _tick() async {
    try {
      final r = await context.read<AuthProvider>().api
          .securityStreamMessages(widget.incidentId, after: _lastId, isClient: widget.isClient);
      final list = ((r['messages'] as List?) ?? const []).cast<Map>();
      if (list.isEmpty || !mounted) return;
      setState(() {
        _msgs.addAll(list);
        if (_msgs.length > 80) _msgs.removeRange(0, _msgs.length - 80);
        _lastId = (list.last['id'] as int?) ?? _lastId;
      });
      _autoScroll();
    } catch (_) {}
  }

  void _autoScroll() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final t = _ctl.text.trim();
    if (t.isEmpty || _sending) return;
    setState(() => _sending = true);
    _ctl.clear();
    try {
      await context.read<AuthProvider>().api
          .securityStreamPostMessage(widget.incidentId, t, isClient: widget.isClient);
      await _tick();
    } catch (_) {}
    if (mounted) setState(() => _sending = false);
  }

  @override
  void dispose() {
    _poll?.cancel();
    _ctl.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final h = widget.compact ? 130.0 : 210.0;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      // الرسائل المنسابة
      SizedBox(height: h, child: ShaderMask(
        shaderCallback: (r) => const LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter,
            colors: [Colors.transparent, Colors.white, Colors.white], stops: [0, .18, 1]).createShader(r),
        blendMode: BlendMode.dstIn,
        child: ListView.builder(
          controller: _scroll, padding: const EdgeInsets.only(bottom: 6),
          itemCount: _msgs.length,
          itemBuilder: (_, i) => _bubble(_msgs[i]),
        ),
      )),
      // حقل الإدخال
      Row(children: [
        Expanded(child: Container(
          decoration: BoxDecoration(color: Colors.black.withValues(alpha: .5), borderRadius: BorderRadius.circular(24),
              border: Border.all(color: Colors.white.withValues(alpha: .18))),
          child: TextField(
            controller: _ctl, style: const TextStyle(color: Colors.white, fontSize: 13.5),
            textInputAction: TextInputAction.send, onSubmitted: (_) => _send(),
            decoration: InputDecoration(
              hintText: tr('أضف تعليقاً…', 'Add a comment…'),
              hintStyle: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 13),
              border: InputBorder.none, isDense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
            ),
          ),
        )),
        const SizedBox(width: 8),
        Material(color: _blue, shape: const CircleBorder(),
            child: InkWell(customBorder: const CircleBorder(), onTap: _send,
                child: Padding(padding: const EdgeInsets.all(11),
                    child: Icon(_sending ? Icons.hourglass_top_rounded : Icons.send_rounded, color: Colors.white, size: 20)))),
      ]),
    ]);
  }

  Widget _bubble(Map m) {
    final kind = '${m['kind'] ?? 'chat'}';
    if (kind == 'system' || kind == 'join') {
      return Padding(padding: const EdgeInsets.symmetric(vertical: 3),
        child: Center(child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(color: Colors.black.withValues(alpha: .4), borderRadius: BorderRadius.circular(10)),
          child: Text('${m['body']}', style: const TextStyle(color: _amber, fontSize: 11.5, fontWeight: FontWeight.w600)),
        )));
    }
    final mine = m['mine'] == true;
    final isClient = m['is_client'] == true;
    return Padding(padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(margin: const EdgeInsets.only(top: 2), padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
          decoration: BoxDecoration(color: Colors.black.withValues(alpha: .5), borderRadius: BorderRadius.circular(12)),
          child: RichText(text: TextSpan(children: [
            TextSpan(text: '${m['name']}${isClient ? ' 🏢' : ''}  ',
                style: TextStyle(color: mine ? _green : _blue, fontWeight: FontWeight.w900, fontSize: 12)),
            TextSpan(text: '${m['body']}', style: const TextStyle(color: Colors.white, fontSize: 13)),
          ])),
        ),
      ]));
  }
}
