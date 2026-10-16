import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/reminder_item.dart';

/// Service managing user reminders, deadlines, and follow-ups.
class ReminderService {
  final ApiClient _client;

  ReminderService(this._client);

  /// Create a new reminder.
  Future<ReminderItem> createReminder({
    required String title,
    String? description,
    required DateTime dueDate,
    String? jobId,
    String reminderType = 'custom',
  }) async {
    final payload = <String, dynamic>{
      'title': title,
      if (description != null && description.isNotEmpty) 'description': description,
      'due_date': dueDate.toUtc().toIso8601String(),
      if (jobId != null && jobId.isNotEmpty) 'job_id': jobId,
      'reminder_type': reminderType,
    };

    final res = await _client.post(
      ApiConfig.remindersEndpoint,
      body: payload,
    );
    return ReminderItem.fromJson(res as Map<String, dynamic>);
  }

  /// Retrieve reminders with optional status filter (active, completed, dismissed, overdue) or job filter.
  Future<List<ReminderItem>> getReminders({
    String? status,
    String? jobId,
  }) async {
    final queryParams = <String, dynamic>{
      if (status != null && status.isNotEmpty) 'status': status,
      if (jobId != null && jobId.isNotEmpty) 'job_id': jobId,
    };

    final res = await _client.get(
      ApiConfig.remindersEndpoint,
      queryParams: queryParams,
    );

    List<dynamic> items = [];
    if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    } else if (res is List) {
      items = res;
    }

    return items
        .map((e) => ReminderItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get single reminder details.
  Future<ReminderItem> getReminder(String id) async {
    final res = await _client.get('${ApiConfig.remindersEndpoint}/$id');
    return ReminderItem.fromJson(res as Map<String, dynamic>);
  }

  /// Update reminder fields.
  Future<ReminderItem> updateReminder(
    String id, {
    String? title,
    String? description,
    DateTime? dueDate,
    String? reminderType,
    bool? isCompleted,
    bool? isDismissed,
  }) async {
    final payload = <String, dynamic>{
      if (title != null) 'title': title,
      if (description != null) 'description': description,
      if (dueDate != null) 'due_date': dueDate.toUtc().toIso8601String(),
      if (reminderType != null) 'reminder_type': reminderType,
      if (isCompleted != null) 'is_completed': isCompleted,
      if (isDismissed != null) 'is_dismissed': isDismissed,
    };

    final res = await _client.patch(
      '${ApiConfig.remindersEndpoint}/$id',
      body: payload,
    );
    return ReminderItem.fromJson(res as Map<String, dynamic>);
  }

  /// Mark reminder as completed.
  Future<ReminderItem> completeReminder(String id) async {
    final res = await _client.post('${ApiConfig.remindersEndpoint}/$id/complete');
    return ReminderItem.fromJson(res as Map<String, dynamic>);
  }

  /// Dismiss reminder.
  Future<ReminderItem> dismissReminder(String id) async {
    final res = await _client.post('${ApiConfig.remindersEndpoint}/$id/dismiss');
    return ReminderItem.fromJson(res as Map<String, dynamic>);
  }

  /// Delete reminder.
  Future<void> deleteReminder(String id) async {
    await _client.delete('${ApiConfig.remindersEndpoint}/$id');
  }
}
