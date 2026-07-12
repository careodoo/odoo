import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Lets a permitted client (or a supervisor) add a worker themselves and attach
/// them to one of their teams. Backend: POST /client/worker/create.
class AddWorkerScreen extends StatefulWidget {
  const AddWorkerScreen({super.key});
  @override
  State<AddWorkerScreen> createState() => _AddWorkerScreenState();
}

class _AddWorkerScreenState extends State<AddWorkerScreen> {
  final _name = TextEditingController();
  final _job = TextEditingController();
  final _phone = TextEditingController();
  final _login = TextEditingController();
  final _password = TextEditingController();

  List<dynamic> _teams = [];
  int? _teamId;
  bool _createLogin = false;
  bool _loading = true, _saving = false;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final d = await context.read<AuthProvider>().api.workerOptions();
      if (!mounted) return;
      setState(() {
        _teams = (d['teams'] as List?) ?? const [];
        _teamId = _teams.isNotEmpty ? _teams.first['id'] as int : null;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _job.dispose();
    _phone.dispose();
    _login.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اسم العامل مطلوب', 'Worker name required'))));
      return;
    }
    setState(() => _saving = true);
    try {
      final r = await context.read<AuthProvider>().api.createWorker({
        'name': _name.text.trim(),
        'job_title': _job.text.trim(),
        'phone': _phone.text.trim(),
        'team_id': _teamId,
        'create_login': _createLogin,
        if (_createLogin) 'login': _login.text.trim(),
        if (_createLogin) 'password': _password.text.trim(),
        if (_createLogin) 'email': _login.text.trim(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('أُضيف العامل: ${r['name']}', 'Worker added: ${r['name']}'))));
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  InputDecoration _dec(String h) => InputDecoration(hintText: h, border: const OutlineInputBorder(), isDense: true);
  Widget _field(String l, Widget c) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(l, style: const TextStyle(fontWeight: FontWeight.w700))),
          c,
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('إضافة عامل', 'Add worker'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              _field(tr('اسم العامل', 'Worker name'), TextField(controller: _name, decoration: _dec(tr('الاسم الكامل', 'Full name')))),
              _field(tr('المسمّى الوظيفي', 'Job title'), TextField(controller: _job, decoration: _dec(tr('مثال: عامل نظافة', 'e.g. Cleaner')))),
              _field(tr('الهاتف', 'Phone'), TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: _dec('+965…'))),
              if (_teams.isNotEmpty)
                _field(tr('الفريق', 'Team'), DropdownButtonFormField<int>(
                  value: _teamId, isExpanded: true, decoration: _dec(''),
                  items: [for (final t in _teams) DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}'))],
                  onChanged: (v) => setState(() => _teamId = v),
                ))
              else
                Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(
                    tr('لا فرق متاحة — سيُضاف العامل لمنشأتك.', 'No teams — worker will be added to your facility.'),
                    style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12.5))),
              Card(child: Column(children: [
                SwitchListTile(
                  value: _createLogin,
                  onChanged: (v) => setState(() => _createLogin = v),
                  secondary: const Icon(Icons.login),
                  title: Text(tr('إنشاء حساب دخول للعامل', 'Create a login for the worker')),
                ),
                if (_createLogin) Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 12), child: Column(children: [
                  TextField(controller: _login, decoration: _dec(tr('اسم الدخول / البريد', 'Login / email'))),
                  const SizedBox(height: 10),
                  TextField(controller: _password, obscureText: true, decoration: _dec(tr('كلمة المرور', 'Password'))),
                ])),
              ])),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _saving ? null : _save,
                icon: _saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.person_add),
                label: Text(tr('إضافة العامل', 'Add worker')),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
              ),
              const SizedBox(height: 24),
            ]),
    );
  }
}
