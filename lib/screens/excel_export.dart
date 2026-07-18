import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Downloads an Odoo `.xlsx` export (reached through the /web/sso bridge, so it
/// runs under the user's real session like the PDF reports) and hands it to the
/// OS share sheet — from which the user can open it in Excel, email it, etc.
///
/// Shows a modal progress dialog, then dismisses. Any screen with an authed API
/// can call [exportExcelFile] from a button.
Future<void> exportExcelFile(
  BuildContext context, {
  required String path, // Odoo path, e.g. /cafm/attendance/export?period=month
  required String fileName, // e.g. attendance-month.xlsx
  String? shareText,
}) async {
  final messenger = ScaffoldMessenger.of(context);
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => const Center(child: _ExportProgress()),
  );
  try {
    final api = context.read<AuthProvider>().api;
    final token = await api.token;
    // Call the report route DIRECTLY with the mobile token — NOT via /web/sso.
    // package:http does not carry the SSO session cookie across the redirect, so
    // the auth='user' target used to bounce to the login page (that was the
    // "error" on print/export). These routes now accept ?token= directly.
    // baseUrl ends with /api/v1; the report routes live at the origin root.
    final origin = api.baseUrl.replaceFirst(RegExp(r'/api/v\d+/?$'), '');
    final sep = path.contains('?') ? '&' : '?';
    final target = '$origin$path${sep}token=${Uri.encodeQueryComponent(token ?? '')}';
    final res = await http.get(Uri.parse(target));
    if (res.statusCode != 200) {
      throw Exception('HTTP ${res.statusCode}');
    }
    final body = res.bodyBytes;
    // A real xlsx is a ZIP: starts with 'PK'. Anything else is an error page.
    if (body.length < 2 || body[0] != 0x50 || body[1] != 0x4B) {
      throw Exception(tr('استجابة غير صالحة', 'Invalid response'));
    }
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/$fileName');
    await file.writeAsBytes(body, flush: true);
    if (context.mounted) Navigator.of(context, rootNavigator: true).pop(); // close progress
    await Share.shareXFiles(
      [XFile(file.path, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')],
      text: shareText ?? fileName,
    );
  } catch (e) {
    if (context.mounted) Navigator.of(context, rootNavigator: true).pop();
    messenger.showSnackBar(SnackBar(
      content: Text(tr('تعذّر تصدير الملف: $e', 'Export failed: $e')),
      backgroundColor: const Color(0xFFC0392B),
      behavior: SnackBarBehavior.floating,
    ));
  }
}

class _ExportProgress extends StatelessWidget {
  const _ExportProgress();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 22),
      margin: const EdgeInsets.symmetric(horizontal: 60),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const SizedBox(
          width: 40, height: 40,
          child: CircularProgressIndicator(strokeWidth: 3, color: Color(0xFF16A34A)),
        ),
        const SizedBox(height: 16),
        Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.grid_on_rounded, color: Color(0xFF16A34A), size: 18),
          const SizedBox(width: 8),
          Text(tr('جارٍ تجهيز ملف Excel…', 'Preparing Excel file…'),
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        ]),
      ]),
    );
  }
}
