import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/notification_item.dart';

/// Service managing in-app notifications and unread badge counters.
class NotificationService {
  final ApiClient _client;

  NotificationService(this._client);

  /// Fetch notifications with optional filters for read status, type, and pagination.
  Future<List<NotificationItem>> getNotifications({
    bool? isRead,
    String? notificationType,
    int limit = 50,
    int offset = 0,
  }) async {
    final queryParams = <String, dynamic>{
      if (isRead != null) 'is_read': isRead.toString(),
      if (notificationType != null && notificationType.isNotEmpty)
        'notification_type': notificationType,
      'limit': limit.toString(),
      'offset': offset.toString(),
    };

    final res = await _client.get(
      ApiConfig.notificationsEndpoint,
      queryParams: queryParams,
    );

    List<dynamic> items = [];
    if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    } else if (res is List) {
      items = res;
    }

    return items
        .map((e) => NotificationItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get the current unread notifications count for badge display.
  Future<int> getUnreadCount() async {
    final res = await _client.get('${ApiConfig.notificationsEndpoint}/unread-count');
    if (res is Map && res.containsKey('unread_count')) {
      return res['unread_count'] as int? ?? 0;
    }
    return 0;
  }

  /// Mark an individual notification as read or unread.
  Future<NotificationItem> markAsRead(String id, {bool isRead = true}) async {
    final res = await _client.patch(
      '${ApiConfig.notificationsEndpoint}/$id/read',
      body: {'is_read': isRead},
    );
    return NotificationItem.fromJson(res as Map<String, dynamic>);
  }

  /// Mark all notifications as read for current user.
  Future<int> markAllAsRead() async {
    final res = await _client.post(
      '${ApiConfig.notificationsEndpoint}/mark-all-read',
    );
    if (res is Map && res.containsKey('updated_count')) {
      return res['updated_count'] as int? ?? 0;
    }
    return 0;
  }

  /// Delete a notification record.
  Future<void> deleteNotification(String id) async {
    await _client.delete('${ApiConfig.notificationsEndpoint}/$id');
  }
}
