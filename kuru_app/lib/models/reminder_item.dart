/// User reminder item model.
class ReminderItem {
  final String id;
  final String firebaseUid;
  final String? jobId;
  final String title;
  final String? description;
  final DateTime dueDate;
  final String reminderType;
  final bool isCompleted;
  final bool isDismissed;
  final bool isOverdue;
  final DateTime? completedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  const ReminderItem({
    required this.id,
    required this.firebaseUid,
    this.jobId,
    required this.title,
    this.description,
    required this.dueDate,
    required this.reminderType,
    required this.isCompleted,
    required this.isDismissed,
    required this.isOverdue,
    this.completedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ReminderItem.fromJson(Map<String, dynamic> json) {
    final parsedDue = json['due_date'] != null
        ? DateTime.tryParse(json['due_date'] as String) ?? DateTime.now()
        : DateTime.now();

    final isComp = json['is_completed'] as bool? ?? false;
    final isDism = json['is_dismissed'] as bool? ?? false;
    final serverOverdue = json['is_overdue'] as bool?;

    final computedOverdue = serverOverdue ?? (!isComp && !isDism && parsedDue.isBefore(DateTime.now()));

    return ReminderItem(
      id: json['id'] as String? ?? '',
      firebaseUid: json['firebase_uid'] as String? ?? '',
      jobId: json['job_id'] as String?,
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      dueDate: parsedDue,
      reminderType: json['reminder_type'] as String? ?? 'custom',
      isCompleted: isComp,
      isDismissed: isDism,
      isOverdue: computedOverdue,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'firebase_uid': firebaseUid,
      'job_id': jobId,
      'title': title,
      'description': description,
      'due_date': dueDate.toIso8601String(),
      'reminder_type': reminderType,
      'is_completed': isCompleted,
      'is_dismissed': isDismissed,
      'is_overdue': isOverdue,
      'completed_at': completedAt?.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  ReminderItem copyWith({
    String? id,
    String? firebaseUid,
    String? jobId,
    String? title,
    String? description,
    DateTime? dueDate,
    String? reminderType,
    bool? isCompleted,
    bool? isDismissed,
    bool? isOverdue,
    DateTime? completedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ReminderItem(
      id: id ?? this.id,
      firebaseUid: firebaseUid ?? this.firebaseUid,
      jobId: jobId ?? this.jobId,
      title: title ?? this.title,
      description: description ?? this.description,
      dueDate: dueDate ?? this.dueDate,
      reminderType: reminderType ?? this.reminderType,
      isCompleted: isCompleted ?? this.isCompleted,
      isDismissed: isDismissed ?? this.isDismissed,
      isOverdue: isOverdue ?? this.isOverdue,
      completedAt: completedAt ?? this.completedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
