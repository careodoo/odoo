import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// A full-screen in-app player for a service video (mp4 URL). Uses an embedded
/// WebView with an HTML5 <video> element — reliable across builds, native
/// controls, no extra native plugins.
class C2CVideoPlayer extends StatefulWidget {
  const C2CVideoPlayer({super.key, required this.url, this.title});
  final String url;
  final String? title;
  @override
  State<C2CVideoPlayer> createState() => _C2CVideoPlayerState();
}

class _C2CVideoPlayerState extends State<C2CVideoPlayer> {
  late final WebViewController _c;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..setNavigationDelegate(NavigationDelegate(
        onPageFinished: (_) { if (mounted) setState(() => _loading = false); },
      ))
      ..loadHtmlString(_html(widget.url));
  }

  String _html(String url) => '''
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;background:#000;display:flex;align-items:center;justify-content:center}
video{width:100%;height:100%;object-fit:contain}</style></head>
<body><video src="$url" controls autoplay playsinline></video></body></html>''';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.title ?? tr('فيديو', 'Video'), style: const TextStyle(fontSize: 15)),
      ),
      body: Stack(children: [
        WebViewWidget(controller: _c),
        if (_loading) const Center(child: CircularProgressIndicator(color: C2C.red)),
      ]),
    );
  }
}

/// A tappable video thumbnail card (poster + play badge) used in rails/galleries.
class C2CVideoThumb extends StatelessWidget {
  const C2CVideoThumb({super.key, required this.url, this.poster, this.title, this.subtitle, this.width = 240, this.height = 150});
  final String url;
  final String? poster, title, subtitle;
  final double width, height;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => C2CVideoPlayer(url: url, title: title))),
      child: Container(
        width: width,
        margin: const EdgeInsets.symmetric(horizontal: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.15), blurRadius: 10, offset: const Offset(0, 5))],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: Stack(children: [
            SizedBox(
              width: width, height: height,
              child: poster != null && '$poster'.startsWith('http')
                  ? Image.network(poster!, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _fallback())
                  : _fallback(),
            ),
            Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                begin: Alignment.topCenter, end: Alignment.bottomCenter,
                colors: [Colors.transparent, Colors.black.withValues(alpha: 0.6)])))),
            const Center(child: CircleAvatar(radius: 22, backgroundColor: Colors.white70,
                child: Icon(Icons.play_arrow_rounded, color: C2C.red, size: 30))),
            if (title != null)
              Positioned(left: 10, right: 10, bottom: 8, child: Column(
                crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(title!, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
                if (subtitle != null)
                  Text(subtitle!, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10.5)),
              ])),
          ]),
        ),
      ),
    );
  }

  Widget _fallback() => Container(
        color: C2C.navy,
        alignment: Alignment.center,
        child: const Icon(Icons.play_circle_outline_rounded, color: Colors.white38, size: 48),
      );
}
