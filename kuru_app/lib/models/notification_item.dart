/// In-app notification item representation.
class NotificationItem {
  final String id;
  final String firebaseUid;
  final String title;
  final String message;
  final String notificationType;
  final String? entityType;
  final String? entityId;
  final bool isRead;
  final Map<String, dynamic> data;
  final DateTime createdAt;
  final DateTime updatedAt;

  const NotificationItem({
    required this.id,
    required this.firebaseUid,
    required this.title,
    required this.message,
    required this.notificationType,
    this.entityType,
    this.entityId,
    required this.isRead,
    required this.data,
    required this.createdAt,
    required this.updatedAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> json) {
    return NotificationItem(
      id: json['id'] as String? ?? '',
      firebaseUid: json['firebase_uid'] as String? ?? '',
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      notificationType: json['notification_type'] as String? ?? 'system',
      entityType: json['entity_type'] as String?,
      entityId: json['entity_id'] as String?,
      isRead: json['is_read'] as bool? ?? false,
      data: (json['data'] as Map<String, dynamic>?) ?? {},
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
      'title': title,
      'message': message,
      'notification_type': notificationType,
      'entity_type': entityType,
      'entity_id': entityId,
      'is_read': isRead,
      'data': data,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  NotificationItem copyWith({
    String? id,
    String? firebaseUid,
    String? title,
    String? message,
    String? notificationType,
    String? entityType,
    String? entityId,
    bool? isRead,
    Map<String, dynamic>? data,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return NotificationItem(
      id: id ?? this.id,
      firebaseUid: firebaseUid ?? this.firebaseUid,
      title: title ?? this.title,
      message: message ?? this.message,
      notificationType: notificationType ?? this.notificationType,
      entityType: entityType ?? this.entityType,
      entityId: entityId ?? this.entityId,
      isRead: isRead ?? this.isRead,
      data: data ?? this.data,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
