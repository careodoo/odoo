import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Real 3D building — renders the Three.js building3d page in a WebView so it's
/// a true rotatable (360°) 3D model with window facades and live occupancy.
class OccupancyScreen extends StatefulWidget {
  const OccupancyScreen({super.key});
  @override
  State<OccupancyScreen> createState() => _OccupancyScreenState();
}

class _OccupancyScreenState extends State<OccupancyScreen> {
  List<dynamic> _facs = [];
  int? _fid;
  String? _token;
  WebViewController? _wc;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final api = context.read<AuthProvider>().api;
      _token = await api.token;
      _facs = await api.facilities();
      if (_facs.isNotEmpty) {
        _fid = _facs.first['id'] as int;
        _loadWeb();
      }
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) setState(() { _loading = false; _error = '$e'; });
    }
  }

  void _loadWeb() {
    final api = context.read<AuthProvider>().api;
    final host = Uri.parse(api.baseUrl).replace(path: '/care_hr/static/mockups/building3d.html', query: null);
    final url = '$host?base=${Uri.encodeComponent(api.baseUrl)}&token=${_token ?? ''}&fid=$_fid';
    _wc = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFEEF4FB))
      ..loadRequest(Uri.parse(url));
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('المبنى ثلاثي الأبعاد', '3D building')),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () => _wc?.reload()),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('${tr('خطأ', 'Error')}: $_error'))
              : _facs.isEmpty
                  ? Center(child: Text(tr('لا مرافق.', 'No facilities.')))
                  : Column(children: [
                      if (_facs.length > 1)
                        Padding(
                          padding: const EdgeInsets.all(10),
                          child: DropdownButtonFormField<int>(
                            value: _fid,
                            decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                            items: [for (final f in _facs) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))],
                            onChanged: (v) { setState(() => _fid = v); _loadWeb(); },
                          ),
                        ),
                      Expanded(child: _wc == null ? const SizedBox() : WebViewWidget(controller: _wc!)),
                      Container(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        alignment: Alignment.center,
                        child: Text(tr('اسحب للدوران 360° · قرّب بالإصبعين · اضغط دوراً لعرض عامليه',
                            'Drag to rotate 360° · pinch to zoom · tap a floor'),
                            style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 11.5)),
                      ),
                    ]),
    );
  }
}
