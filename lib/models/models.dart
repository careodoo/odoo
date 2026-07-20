import '../core/i18n.dart';
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

class Counts {
  Counts({this.open = 0, this.inProgress = 0, this.done = 0, this.overdue = 0, this.total = 0});
  final int open, inProgress, done, overdue, total;
  factory Counts.fromJson(Map j) => Counts(
        open: j['open'] as int? ?? 0,
        inProgress: j['in_progress'] as int? ?? 0,
        done: j['done'] as int? ?? 0,
        overdue: j['overdue'] as int? ?? 0,
        total: j['total'] as int? ?? 0,
      );
}

class Profile {
  Profile({
    required this.userId,
    required this.name,
    required this.login,
    required this.role,
    required this.isSupervisor,
    this.isQuality = false,
    required this.isAdmin,
    required this.canAddWorkers,
    required this.serviceTypes,
    required this.services,
    required this.counts,
    required this.unreadNotifications,
    this.employeeId,
  });
  final int userId;
  final String name;
  final String login;
  final String role;
  final bool isSupervisor;
  /// named on a team's quality slot → gets the inspection console
  final bool isQuality;
  final bool isAdmin;
  final bool canAddWorkers;
  final List<String> serviceTypes;
  final List<Service> services;
  final Counts counts;
  final int unreadNotifications;
  final int? employeeId;

  int get openWorkOrders => counts.open;

  factory Profile.fromJson(Map j) {
    final u = (j['user'] as Map?) ?? {};
    return Profile(
      userId: u['id'] as int? ?? 0,
      name: u['name'] as String? ?? '',
      login: u['login'] as String? ?? '',
      employeeId: u['employee_id'] as int?,
      role: j['role'] as String? ?? 'worker',
      isSupervisor: j['is_supervisor'] as bool? ?? false,
      isQuality: j['is_quality'] as bool? ?? false,
      isAdmin: j['is_admin'] as bool? ?? false,
      canAddWorkers: j['can_add_workers'] as bool? ?? false,
      serviceTypes: List<String>.from((j['my_service_types'] as List?) ?? const []),
      services: [for (final s in (j['services'] as List? ?? const [])) Service.fromJson(s as Map)],
      counts: Counts.fromJson((j['counts'] as Map?) ?? const {}),
      unreadNotifications: j['unread_notifications'] as int? ?? 0,
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
        durationMinutes: dblOf(j['duration_minutes'], 0.0),
      );
}
