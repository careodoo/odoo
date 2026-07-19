import 'package:flutter/material.dart';

import '../screens/pdf_report_screen.dart';
import 'i18n.dart';

/// Opening any record's PDF report, from anywhere.
///
/// The backend renders a report for every model rather than one route per
/// service, so the app only needs the model code and the id. Screens call
/// [openRecordReport] or drop a [ReportButton] into an app bar — nobody has to
/// remember a per-service URL again.
Future<void> openRecordReport(
  BuildContext context, {
  required String code,
  required int id,
  required String title,
}) {
  return Navigator.push(
    context,
    MaterialPageRoute(
      builder: (_) => PdfReportScreen(
        path: '/api/v1/report/$code/$id',
        title: title,
        fileName: '$code-$id.pdf',
      ),
    ),
  );
}

/// The standard "print this record" action. Put it in a record screen's
/// app bar; it looks the same everywhere so users learn it once.
class ReportButton extends StatelessWidget {
  const ReportButton({
    super.key,
    required this.code,
    required this.id,
    required this.title,
    this.compact = false,
  });

  final String code;
  final int id;
  final String title;

  /// A bare icon for a crowded app bar, instead of an icon with a label.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final label = tr('التقرير', 'Report');
    if (compact) {
      return IconButton(
        tooltip: label,
        icon: const Icon(Icons.picture_as_pdf_outlined),
        onPressed: () => openRecordReport(context, code: code, id: id, title: title),
      );
    }
    return TextButton.icon(
      icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
      label: Text(label),
      onPressed: () => openRecordReport(context, code: code, id: id, title: title),
    );
  }
}
