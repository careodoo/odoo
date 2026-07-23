import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth.dart';
import 'i18n.dart';

/// A single, reusable in-app **account deletion** flow (App Store Guideline
/// 5.1.1(v)). Every settings/account surface calls this so the option is always
/// reachable. It: explains what happens, takes an optional reason, requires an
/// explicit confirmation, submits the deletion request, then signs the user out.
Future<void> showDeleteAccountFlow(BuildContext context) async {
  final auth = context.read<AuthProvider>();
  final reason = TextEditingController();
  const red = Color(0xFFB91C1C);

  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Row(children: [
        const Icon(Icons.delete_forever_rounded, color: red),
        const SizedBox(width: 8),
        Expanded(child: Text(tr('حذف الحساب', 'Delete account'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17))),
      ]),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr(
          'سيؤدي هذا إلى حذف حسابك وكل بياناتك الشخصية نهائيًا خلال 30 يومًا. لا يمكن التراجع عن هذا الإجراء.',
          'This permanently deletes your account and all your personal data within 30 days. This action cannot be undone.'),
          style: const TextStyle(height: 1.6, fontSize: 13.5)),
        const SizedBox(height: 14),
        TextField(
          controller: reason,
          maxLines: 2,
          decoration: InputDecoration(
            labelText: tr('سبب الحذف (اختياري)', 'Reason (optional)'),
            border: const OutlineInputBorder(),
            isDense: true,
          ),
        ),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(backgroundColor: red, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, true),
          icon: const Icon(Icons.delete_forever_rounded, size: 18),
          label: Text(tr('متابعة الحذف', 'Continue')),
        ),
      ],
    ),
  );
  if (confirmed != true || !context.mounted) return;

  // second, explicit confirmation to prevent accidental deletion
  final finalOk = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('تأكيد نهائي', 'Final confirmation'),
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Text(tr('هل أنت متأكد من حذف حسابك؟ سيتم تسجيل خروجك فورًا.',
          'Are you sure you want to delete your account? You will be signed out immediately.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('تراجع', 'Back'))),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: red, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, true),
          child: Text(tr('نعم، احذف حسابي', 'Yes, delete my account')),
        ),
      ],
    ),
  );
  if (finalOk != true || !context.mounted) return;

  try {
    await auth.api.accountDeleteRequest(reason: reason.text.trim());
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم استلام طلب حذف الحساب — سيتم تسجيل خروجك',
            'Account deletion requested — signing out')),
        backgroundColor: const Color(0xFF16A34A)));
    }
    await auth.logout();
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('$e'), backgroundColor: red));
    }
  }
}
