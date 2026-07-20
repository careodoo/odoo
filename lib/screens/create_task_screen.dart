import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'searchable_picker.dart';

/// Full-page task creation for supervisors — opens as its own screen (not an
/// inline list row). Captures the assignee, "المطلوب تنفيذه", and the proof
/// the worker must submit before the result can be approved.
class CreateTaskScreen extends StatefulWidget {
  const CreateTaskScreen({super.key, this.presetEmployeeId, this.presetEmployeeName});
  final int? presetEmployeeId;
  final String? presetEmployeeName;
  @override
  State<CreateTaskScreen> createState() => _CreateTaskScreenState();
}

class _CreateTaskScreenState extends State<CreateTaskScreen> {
  final _title = TextEditingController();
  final _instructions = TextEditingController();
  final _minutes = TextEditingController(text: '60');

  List<dynamic> _employees = [], _services = [], _facilities = [];
  int? _empId, _serviceId, _facilityId;
  int _priority = 1;
  bool _presence = true, _photo = true, _video = false;
  bool _loading = true, _saving = false;

  @override
  void initState() {
    super.initState();
    _empId = widget.presetEmployeeId;
    _boot();
  }

  Future<void> _boot() async {
    final api = context.read<AuthProvider>().api;
    try {
      final res = await Future.wait([api.employees(), api.servicesCatalog(), api.facilities()]);
      if (!mounted) return;
      setState(() {
        _employees = res[0];
        _services = res[1];
        _facilities = res[2];
        _serviceId = _services.isNotEmpty ? _services.first['id'] as int : null;
        _facilityId = _facilities.isNotEmpty ? _facilities.first['id'] as int : null;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _title.dispose();
    _instructions.dispose();
    _minutes.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_title.text.trim().isEmpty || _empId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('العنوان والموظف مطلوبان', 'Title and employee are required'))));
      return;
    }
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.createWorkOrder({
        'title': _title.text.trim(),
        'employee_id': _empId,
        'service_id': _serviceId,
        'facility_id': _facilityId,
        'priority': _priority,
        'expected_minutes': int.tryParse(_minutes.text) ?? 60,
        'instructions': _instructions.text.trim(),
        'proof_presence': _presence,
        'proof_photo': _photo,
        'proof_video': _video,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم إنشاء المهمة وإسنادها', 'Task created & assigned'))));
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('مهمة جديدة', 'New task'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              _field(tr('عنوان المهمة', 'Task title'), TextField(controller: _title, decoration: _dec(tr('مثال: تنظيف الواجهة', 'e.g. facade cleaning')))),
              _field(tr('الموظف المُسنَد إليه', 'Assign to'), SearchableField(
                label: tr('الموظف المُسنَد إليه', 'Assign to'), icon: Icons.person_rounded, value: _empId, allowClear: false,
                options: [for (final e in _employees) PickOption(value: e['id'], label: '${e['name']}',
                    sublabel: e['job_title'] != null ? '${e['job_title']}' : null)],
                onChanged: (v) => setState(() => _empId = v as int?))),
              Row(children: [
                Expanded(child: _field(tr('الخدمة', 'Service'), SearchableField(
                  label: tr('الخدمة', 'Service'), icon: Icons.design_services_rounded, value: _serviceId, allowClear: false,
                  options: [for (final s in _services) PickOption(value: s['id'], label: '${s['name']}')],
                  onChanged: (v) => setState(() => _serviceId = v as int?)))),
                const SizedBox(width: 10),
                Expanded(child: _field(tr('المرفق', 'Facility'), SearchableField(
                  label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: _facilityId, allowClear: false,
                  options: [for (final f in _facilities) PickOption(value: f['id'], label: '${f['name']}')],
                  onChanged: (v) => setState(() => _facilityId = v as int?)))),
              ]),
              Row(children: [
                Expanded(child: _dropdown<int>(tr('الأولوية', 'Priority'), _priority, [
                  DropdownMenuItem(value: 0, child: Text(tr('عادية', 'Normal'))),
                  DropdownMenuItem(value: 1, child: Text(tr('متوسطة', 'Medium'))),
                  DropdownMenuItem(value: 2, child: Text(tr('عالية', 'High'))),
                  DropdownMenuItem(value: 3, child: Text(tr('عاجلة', 'Urgent'))),
                ], (v) => setState(() => _priority = v ?? 1))),
                const SizedBox(width: 10),
                Expanded(child: _field(tr('المدة (دقيقة)', 'Minutes'),
                    TextField(controller: _minutes, keyboardType: TextInputType.number, decoration: _dec('60')))),
              ]),
              _field(tr('المطلوب تنفيذه', 'What to do'),
                  TextField(controller: _instructions, maxLines: 4, decoration: _dec(tr('التعليمات التفصيلية للعامل…', 'Detailed instructions for the worker…')))),
              const SizedBox(height: 8),
              Text(tr('إثبات الإنجاز المطلوب', 'Required completion proof'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              Card(child: Column(children: [
                SwitchListTile(value: _presence, onChanged: (v) => setState(() => _presence = v),
                    secondary: const Icon(Icons.qr_code_scanner), title: Text(tr('إثبات حضور بمسح QR الموقع', 'Presence via location QR'))),
                SwitchListTile(value: _photo, onChanged: (v) => setState(() => _photo = v),
                    secondary: const Icon(Icons.photo_camera), title: Text(tr('صورة', 'Photo'))),
                SwitchListTile(value: _video, onChanged: (v) => setState(() => _video = v),
                    secondary: const Icon(Icons.videocam), title: Text(tr('فيديو', 'Video'))),
              ])),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _saving ? null : _save,
                icon: _saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.check),
                label: Text(tr('إنشاء وإسناد', 'Create & assign')),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
              ),
              const SizedBox(height: 24),
            ]),
    );
  }

  InputDecoration _dec(String hint) => InputDecoration(hintText: hint, border: const OutlineInputBorder(), isDense: true);

  Widget _field(String label, Widget child) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
          child,
        ]),
      );

  Widget _dropdown<T>(String label, T? value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onChanged) => _field(
        label,
        DropdownButtonFormField<T>(
          value: value, isExpanded: true, items: items, onChanged: onChanged,
          decoration: _dec(''),
        ),
      );
}
