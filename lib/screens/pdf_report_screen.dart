import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:printing/printing.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// In-app PDF report viewer.
///
/// Fetches the report with the API token (an external browser has no token, so
/// the PDF must be downloaded here) and renders it inside the app with share
/// and print actions.
class PdfReportScreen extends StatefulWidget {
  const PdfReportScreen({super.key, required this.path, required this.title, this.fileName});

  /// Odoo path, e.g. /waste/order/219/report — fetched via SSO with the token.
  final String path;
  final String title;
  final String? fileName;

  @override
  State<PdfReportScreen> createState() => _PdfReportScreenState();
}

class _PdfReportScreenState extends State<PdfReportScreen> {
  Uint8List? _bytes;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() { _error = null; _bytes = null; });
    try {
      final api = context.read<AuthProvider>().api;
      final token = await api.token;
      // Reuse the SSO bridge: it establishes a session for the token and
      // redirects to the report, so the PDF comes back on the same request.
      // NOTE: api.baseUrl already ends with /api/v1 — never re-add it.
      final url = '${api.baseUrl}/web/sso'
          '?token=${Uri.encodeQueryComponent(token ?? '')}'
          '&redirect=${Uri.encodeQueryComponent(widget.path)}';
      final res = await http.get(Uri.parse(url));
      final body = res.bodyBytes;
      final isPdf = body.length > 4 &&
          body[0] == 0x25 && body[1] == 0x50 && body[2] == 0x44 && body[3] == 0x46; // %PDF
      if (res.statusCode != 200 || !isPdf) {
        throw Exception(tr('تعذّر تحميل التقرير (${res.statusCode})',
                           'Could not load the report (${res.statusCode})'));
      }
      if (mounted) setState(() => _bytes = body);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    const navy = Color(0xFF0E3A5F);
    final name = widget.fileName ?? 'report.pdf';
    return Scaffold(
      backgroundColor: const Color(0xFFECEFF3),
      appBar: AppBar(
        backgroundColor: navy, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
        actions: [
          if (_bytes != null) ...[
            IconButton(
              tooltip: tr('مشاركة', 'Share'),
              icon: const Icon(Icons.share_rounded),
              onPressed: () => Printing.sharePdf(bytes: _bytes!, filename: name),
            ),
            IconButton(
              tooltip: tr('طباعة', 'Print'),
              icon: const Icon(Icons.print_rounded),
              onPressed: () => Printing.layoutPdf(onLayout: (_) async => _bytes!, name: name),
            ),
          ],
        ],
      ),
      body: _error != null
          ? _errorView()
          : _bytes == null
              ? const Center(child: CircularProgressIndicator())
              : PdfPreview(
                  build: (_) async => _bytes!,
                  useActions: false, // our AppBar carries share/print
                  canChangePageFormat: false,
                  canChangeOrientation: false,
                  canDebug: false,
                  maxPageWidth: 900,
                  pdfFileName: name,
                  loadingWidget: const CircularProgressIndicator(),
                ),
      bottomNavigationBar: _bytes == null ? null : SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
          child: Row(children: [
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: navy, side: const BorderSide(color: navy),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: () => Printing.sharePdf(bytes: _bytes!, filename: name),
              icon: const Icon(Icons.share_rounded, size: 18),
              label: Text(tr('مشاركة', 'Share'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
            const SizedBox(width: 10),
            Expanded(child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: navy, foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: () => Printing.layoutPdf(onLayout: (_) async => _bytes!, name: name),
              icon: const Icon(Icons.print_rounded, size: 18),
              label: Text(tr('طباعة', 'Print'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
          ]),
        ),
      ),
    );
  }

  Widget _errorView() => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.picture_as_pdf_outlined, size: 56, color: Colors.grey),
            const SizedBox(height: 12),
            Text(tr('تعذّر عرض التقرير', 'Could not display the report'),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 6),
            Text('$_error', textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey, fontSize: 12)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _fetch,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(tr('إعادة المحاولة', 'Retry')),
            ),
          ]),
        ),
      );
}
