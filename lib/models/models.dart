/// Plain data models mirroring the `/api/v1` JSON.

class Service {
  Service({required this.id, required this.name, required this.type, this.icon});
  final int id;
  final String name;
  final String type;
  final String? icon;
  factory Service.fromJson(Map j) => Service(
        id: j['id'] as int,
        name: j['name'] as String? ?? '',
        type: j['type'] as String? ?? 'other',
        icon: j['icon'] as String?,
      );
}

class Profile {
  Profile({
    required this.userId,
    required this.name,
    required this.login,
    required this.role,
    required this.serviceTypes,
    required this.services,
    required this.openWorkOrders,
    this.employeeId,
  });
  final int userId;
  final String name;
  final String login;
  final String role;
  final List<String> serviceTypes;
  final List<Service> services;
  final int openWorkOrders;
  final int? employeeId;

  factory Profile.fromJson(Map j) {
    final u = (j['user'] as Map?) ?? {};
    final counts = (j['counts'] as Map?) ?? {};
    return Profile(
      userId: u['id'] as int? ?? 0,
      name: u['name'] as String? ?? '',
      login: u['login'] as String? ?? '',
      employeeId: u['employee_id'] as int?,
      role: j['role'] as String? ?? 'worker',
      serviceTypes: List<String>.from((j['my_service_types'] as List?) ?? const []),
      services: [for (final s in (j['services'] as List? ?? const [])) Service.fromJson(s as Map)],
      openWorkOrders: counts['open_workorders'] as int? ?? 0,
    );
  }
}

class WorkOrder {
  WorkOrder({
    required this.id,
    required this.name,
    required this.title,
    required this.facility,
    required this.serviceType,
    required this.priority,
    required this.state,
    this.location,
    this.deadline,
    this.startDatetime,
    this.doneDatetime,
    this.durationMinutes = 0,
  });
  final int id;
  final String name;
  final String title;
  final String facility;
  final String? location;
  final String serviceType;
  final String priority;
  final String state;
  final String? deadline;
  final String? startDatetime;
  final String? doneDatetime;
  final double durationMinutes;

  bool get isOpen => !['done', 'verified', 'cancelled'].contains(state);
  bool get inProgress => state == 'in_progress';

  factory WorkOrder.fromJson(Map j) => WorkOrder(
        id: j['id'] as int,
        name: j['name'] as String? ?? '',
        title: j['title'] as String? ?? '',
        facility: j['facility'] as String? ?? '',
        location: j['location'] as String?,
        serviceType: j['service_type'] as String? ?? 'other',
        priority: (j['priority'] ?? '1').toString(),
        state: j['state'] as String? ?? 'new',
        deadline: j['deadline'] as String?,
        startDatetime: j['start_datetime'] as String?,
        doneDatetime: j['done_datetime'] as String?,
        durationMinutes: (j['duration_minutes'] as num?)?.toDouble() ?? 0,
      );
}
