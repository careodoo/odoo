import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/i18n.dart';

/// Full-screen, in-app viewer for work-order media.
/// Images are zoomable (InteractiveViewer); videos play inside a WebView.
/// Every item can be shared or downloaded to the device.
class MediaViewerScreen extends StatefulWidget {
  const MediaViewerScreen({super.key, required this.media, this.index = 0, this.token});
  final List<Map> media;
  final int index;
  final String? token;

  @override
  State<MediaViewerScreen> createState() => _MediaViewerScreenState();
}

class _MediaViewerScreenState extends State<MediaViewerScreen> {
  late final PageController _pc = PageController(initialPage: widget.index);
  late int _i = widget.index;
  bool _busy = false;

  bool _isVideo(Map m) {
    final t = '${m['type'] ?? ''}'.toLowerCase();
    final u = '${m['url'] ?? ''}'.toLowerCase();
    return t.contains('video') || u.endsWith('.mp4') || u.endsWith('.mov') || u.endsWith('.webm');
  }

  Map get _cur => widget.media[_i];

  Future<File> _download(Map m) async {
    final url = '${m['url']}';
    final res = await http.get(Uri.parse(url),
        headers: widget.token != null ? {'Authorization': 'Bearer ${widget.token}'} : null);
    final dir = await getTemporaryDirectory();
    final name = ('${m['name'] ?? ''}'.trim().isNotEmpty)
        ? '${m['name']}'.replaceAll(RegExp(r'[^\w.\-]'), '_')
        : 'care_${_isVideo(m) ? 'video.mp4' : 'photo.jpg'}';
    final f = File('${dir.path}/$name');
    await f.writeAsBytes(res.bodyBytes);
    return f;
  }

  Future<void> _share() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final f = await _download(_cur);
      await Share.shareXFiles([XFile(f.path)]);
    } catch (e) {
      _snack(tr('تعذّرت المشاركة', 'Share failed'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final f = await _download(_cur);
      // move to a Downloads-style visible directory when available
      Directory? out;
      try {
        out = Directory('/storage/emulated/0/Download');
        if (!await out.exists()) out = await getExternalStorageDirectory();
      } catch (_) {
        out = await getApplicationDocumentsDirectory();
      }
      out ??= await getApplicationDocumentsDirectory();
      final dest = File('${out.path}/${f.uri.pathSegments.last}');
      await dest.writeAsBytes(await f.readAsBytes());
      _snack(tr('تم الحفظ: ${dest.path}', 'Saved: ${dest.path}'));
    } catch (e) {
      _snack(tr('تعذّر الحفظ', 'Download failed'));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text('${_i + 1} / ${widget.media.length}'),
        actions: [
          IconButton(onPressed: _busy ? null : _share, icon: const Icon(Icons.share)),
          IconButton(onPressed: _busy ? null : _save, icon: const Icon(Icons.download)),
        ],
      ),
      body: Stack(children: [
        PageView.builder(
          controller: _pc,
          itemCount: widget.media.length,
          onPageChanged: (v) => setState(() => _i = v),
          itemBuilder: (_, i) {
            final m = widget.media[i];
            if (_isVideo(m)) return _VideoView(url: '${m['url']}');
            return InteractiveViewer(
              minScale: 0.8,
              maxScale: 5,
              child: Center(
                child: Image.network('${m['url']}',
                    fit: BoxFit.contain,
                    loadingBuilder: (_, w, p) => p == null ? w : const Center(child: CircularProgressIndicator(color: Colors.white)),
                    errorBuilder: (_, __, ___) => const Icon(Icons.broken_image, color: Colors.white54, size: 60)),
              ),
            );
          },
        ),
        if (_busy) const Positioned.fill(child: ColoredBox(color: Colors.black38, child: Center(child: CircularProgressIndicator(color: Colors.white)))),
      ]),
    );
  }
}

class _VideoView extends StatefulWidget {
  const _VideoView({required this.url});
  final String url;
  @override
  State<_VideoView> createState() => _VideoViewState();
}

class _VideoViewState extends State<_VideoView> {
  late final WebViewController _c;
  @override
  void initState() {
    super.initState();
    final html =
        '<html><body style="margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh">'
        '<video src="${widget.url}" controls autoplay playsinline style="max-width:100%;max-height:100%"></video></body></html>';
    _c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..loadHtmlString(html);
  }

  @override
  Widget build(BuildContext context) => WebViewWidget(controller: _c);
}
