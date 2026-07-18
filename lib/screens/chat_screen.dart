import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

const _navy = Color(0xFF0E3A5F);
const _accent = Color(0xFF0E7490);

/// التواصل — recent conversations + a live people-directory search. Tapping a
/// person or thread opens the 1:1 chat.
class ChatHubScreen extends StatefulWidget {
  const ChatHubScreen({super.key});
  @override
  State<ChatHubScreen> createState() => _ChatHubScreenState();
}

class _ChatHubScreenState extends State<ChatHubScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: const Color(0xFFF4F6FA),
        appBar: AppBar(
          backgroundColor: _accent, foregroundColor: Colors.white,
          title: Text(tr('التواصل', 'Messages'), style: const TextStyle(fontWeight: FontWeight.w900)),
          bottom: TabBar(indicatorColor: Colors.white, labelColor: Colors.white, unselectedLabelColor: Colors.white70,
            labelStyle: const TextStyle(fontWeight: FontWeight.w900),
            tabs: [Tab(text: tr('المحادثات', 'Chats')), Tab(text: tr('الدليل', 'Directory'))]),
        ),
        body: const TabBarView(children: [_ThreadsTab(), _DirectoryTab()]),
      ),
    );
  }
}

class _ThreadsTab extends StatefulWidget {
  const _ThreadsTab();
  @override
  State<_ThreadsTab> createState() => _ThreadsTabState();
}

class _ThreadsTabState extends State<_ThreadsTab> with AutomaticKeepAliveClientMixin {
  Future<List<dynamic>>? _future;
  @override
  bool get wantKeepAlive => true;
  @override
  void initState() { super.initState(); _load(); }
  void _load() => setState(() => _future = context.read<AuthProvider>().api.chatThreads());

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return RefreshIndicator(
      color: _accent, onRefresh: () async => _load(),
      child: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _accent));
          final t = snap.data!;
          if (t.isEmpty) return ListView(children: [const SizedBox(height: 120), Icon(Icons.forum_rounded, size: 56, color: Colors.grey.shade300), const SizedBox(height: 10), Center(child: Text(tr('لا محادثات — ابدأ من الدليل', 'No chats — start from Directory'), style: TextStyle(color: Colors.grey.shade500)))]);
          return ListView.builder(padding: const EdgeInsets.all(10), itemCount: t.length, itemBuilder: (_, i) => _tile(t[i] as Map));
        },
      ),
    );
  }

  Widget _tile(Map th) {
    final peer = (th['peer'] as Map?) ?? {};
    final unread = (th['unread'] as num?)?.toInt() ?? 0;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        leading: CircleAvatar(backgroundColor: _navy, child: Text('${peer['name'] ?? '?'}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
        title: Text('${peer['name'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w800)),
        subtitle: Text('${th['last'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: unread > 0
            ? Container(padding: const EdgeInsets.all(6), decoration: const BoxDecoration(color: _accent, shape: BoxShape.circle), child: Text('$unread', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)))
            : const Icon(Icons.chevron_left_rounded, color: Colors.grey),
        onTap: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(peerUid: _i(peer['uid']), peerName: '${peer['name'] ?? ''}')));
          _load();
        },
      ),
    );
  }
}

class _DirectoryTab extends StatefulWidget {
  const _DirectoryTab();
  @override
  State<_DirectoryTab> createState() => _DirectoryTabState();
}

class _DirectoryTabState extends State<_DirectoryTab> with AutomaticKeepAliveClientMixin {
  Future<List<dynamic>>? _future;
  Timer? _debounce;
  @override
  bool get wantKeepAlive => true;
  @override
  void initState() { super.initState(); _search(''); }

  void _search(String q) => setState(() => _future = context.read<AuthProvider>().api.directory(q: q));

  void _onChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () => _search(v));
  }

  @override
  void dispose() { _debounce?.cancel(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(10),
        child: TextField(
          autofocus: false,
          onChanged: _onChanged,
          decoration: InputDecoration(
            hintText: tr('ابحث عن أي شخص بالاسم أو الوظيفة…', 'Search anyone by name or job…'),
            prefixIcon: const Icon(Icons.search_rounded), filled: true, fillColor: Colors.white, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          ),
        ),
      ),
      Expanded(child: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _accent));
          final list = snap.data!;
          if (list.isEmpty) return Center(child: Text(tr('لا نتائج', 'No results'), style: TextStyle(color: Colors.grey.shade500)));
          return ListView.builder(padding: const EdgeInsets.symmetric(horizontal: 10), itemCount: list.length, itemBuilder: (_, i) {
            final u = list[i] as Map;
            return Card(margin: const EdgeInsets.symmetric(vertical: 4), child: ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              leading: CircleAvatar(backgroundColor: _accent, child: Text('${u['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
              title: Text('${u['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
              subtitle: Text([u['job'], u['department']].where((x) => x != null).join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis),
              trailing: const Icon(Icons.chat_bubble_outline_rounded, color: _accent, size: 20),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(peerUid: _i(u['uid']), peerName: '${u['name']}'))),
            ));
          });
        },
      )),
    ]);
  }
}

/// A 1:1 conversation thread with a send box; polls for new messages.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.peerUid, required this.peerName});
  final int peerUid;
  final String peerName;
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  List<dynamic> _messages = [];
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  Timer? _poll;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 6), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _poll?.cancel();
    _ctrl.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    try {
      final d = await context.read<AuthProvider>().api.chatMessages(widget.peerUid);
      if (!mounted) return;
      final msgs = (d['messages'] as List?) ?? [];
      final changed = msgs.length != _messages.length;
      setState(() => _messages = msgs);
      if (changed) _toBottom();
    } catch (_) {}
  }

  void _toBottom() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      });

  Future<void> _send() async {
    final body = _ctrl.text.trim();
    if (body.isEmpty) return;
    setState(() => _sending = true);
    _ctrl.clear();
    try {
      await context.read<AuthProvider>().api.chatSend(widget.peerUid, body);
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFECF0F5),
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white,
        title: Row(children: [
          CircleAvatar(radius: 16, backgroundColor: Colors.white24, child: Text(widget.peerName.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13))),
          const SizedBox(width: 10),
          Expanded(child: Text(widget.peerName, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16), maxLines: 1, overflow: TextOverflow.ellipsis)),
        ]),
      ),
      body: Column(children: [
        Expanded(child: _messages.isEmpty
            ? Center(child: Text(tr('ابدأ المحادثة', 'Start the conversation'), style: TextStyle(color: Colors.grey.shade500)))
            : ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.all(12),
                itemCount: _messages.length,
                itemBuilder: (_, i) => _bubble(_messages[i] as Map),
              )),
        SafeArea(top: false, child: Container(
          padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
          color: Colors.white,
          child: Row(children: [
            Expanded(child: TextField(
              controller: _ctrl, minLines: 1, maxLines: 4,
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: tr('اكتب رسالة…', 'Type a message…'), filled: true, fillColor: const Color(0xFFF1F3F6), isDense: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
            )),
            const SizedBox(width: 8),
            Material(color: _accent, shape: const CircleBorder(), child: InkWell(
              customBorder: const CircleBorder(),
              onTap: _sending ? null : _send,
              child: Padding(padding: const EdgeInsets.all(11),
                child: _sending ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.send_rounded, color: Colors.white, size: 20)),
            )),
          ]),
        )),
      ]),
    );
  }

  Widget _bubble(Map m) {
    final mine = m['mine'] == true;
    return Align(
      alignment: mine ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.76),
        decoration: BoxDecoration(
          color: mine ? _accent : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16), topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(mine ? 4 : 16), bottomRight: Radius.circular(mine ? 16 : 4)),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 4, offset: const Offset(0, 2))],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${m['body']}', style: TextStyle(color: mine ? Colors.white : _navy, fontSize: 14, height: 1.3)),
          const SizedBox(height: 3),
          Text('${m['at'] ?? ''}'.replaceFirst('T', ' ').padRight(16).substring(0, 16),
              style: TextStyle(color: mine ? Colors.white70 : Colors.grey.shade500, fontSize: 9.5)),
        ]),
      ),
    );
  }
}

int _i(dynamic v) => v is int ? v : (v is num ? v.toInt() : int.tryParse('$v') ?? 0);
