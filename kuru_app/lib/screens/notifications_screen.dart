import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/notification_item.dart';
import '../models/reminder_item.dart';
import '../services/notification_service.dart';
import '../services/reminder_service.dart';
import 'widgets/state_views.dart';

class NotificationsScreen extends StatefulWidget {
  final NotificationService notificationService;
  final ReminderService reminderService;

  const NotificationsScreen({
    super.key,
    required this.notificationService,
    required this.reminderService,
  });

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  List<NotificationItem> _notifications = [];
  List<ReminderItem> _reminders = [];

  bool _isLoadingNotifications = false;
  bool _isLoadingReminders = false;
  String? _notificationsError;
  String? _remindersError;

  String? _selectedReminderStatus; // null, 'active', 'overdue', 'completed'

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 1 && _reminders.isEmpty && !_isLoadingReminders) {
        _loadReminders();
      }
    });
    _loadNotifications();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadNotifications() async {
    setState(() {
      _isLoadingNotifications = true;
      _notificationsError = null;
    });

    try {
      final items = await widget.notificationService.getNotifications();
      setState(() => _notifications = items);
    } catch (e) {
      setState(() => _notificationsError = e.toString());
    } finally {
      if (mounted) setState(() => _isLoadingNotifications = false);
    }
  }

  Future<void> _loadReminders() async {
    setState(() {
      _isLoadingReminders = true;
      _remindersError = null;
    });

    try {
      final items = await widget.reminderService.getReminders(
        status: _selectedReminderStatus,
      );
      setState(() => _reminders = items);
    } catch (e) {
      setState(() => _remindersError = e.toString());
    } finally {
      if (mounted) setState(() => _isLoadingReminders = false);
    }
  }

  Future<void> _markAsRead(NotificationItem item) async {
    if (item.isRead) return;
    try {
      await widget.notificationService.markAsRead(item.id, isRead: true);
      setState(() {
        _notifications = _notifications
            .map((n) => n.id == item.id ? n.copyWith(isRead: true) : n)
            .toList();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to mark read: $e')),
      );
    }
  }

  Future<void> _markAllRead() async {
    try {
      final count = await widget.notificationService.markAllAsRead();
      setState(() {
        _notifications = _notifications.map((n) => n.copyWith(isRead: true)).toList();
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$count notifications marked as read')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to mark all read: $e')),
      );
    }
  }

  Future<void> _deleteNotification(String id) async {
    try {
      await widget.notificationService.deleteNotification(id);
      setState(() {
        _notifications.removeWhere((n) => n.id == id);
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete notification: $e')),
      );
    }
  }

  Future<void> _completeReminder(ReminderItem item) async {
    try {
      final updated = await widget.reminderService.completeReminder(item.id);
      setState(() {
        _reminders = _reminders.map((r) => r.id == item.id ? updated : r).toList();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to complete reminder: $e')),
      );
    }
  }

  Future<void> _dismissReminder(ReminderItem item) async {
    try {
      final updated = await widget.reminderService.dismissReminder(item.id);
      setState(() {
        _reminders = _reminders.map((r) => r.id == item.id ? updated : r).toList();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to dismiss reminder: $e')),
      );
    }
  }

  Future<void> _deleteReminder(String id) async {
    try {
      await widget.reminderService.deleteReminder(id);
      setState(() {
        _reminders.removeWhere((r) => r.id == id);
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete reminder: $e')),
      );
    }
  }

  void _showCreateReminderDialog() {
    final titleController = TextEditingController();
    final descController = TextEditingController();
    DateTime selectedDate = DateTime.now().add(const Duration(days: 1));
    String reminderType = 'custom';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
            left: 20,
            right: 20,
            top: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Create New Reminder',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Reminder Title *',
                  hintText: 'e.g., Send follow-up email to hiring manager',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: descController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Description (Optional)',
                  hintText: 'Details, key discussion points, or links',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Text('Type: ', style: TextStyle(fontWeight: FontWeight.w600)),
                  DropdownButton<String>(
                    value: reminderType,
                    items: const [
                      DropdownMenuItem(value: 'custom', child: Text('Custom')),
                      DropdownMenuItem(value: 'follow_up', child: Text('Follow-up')),
                      DropdownMenuItem(value: 'deadline', child: Text('Deadline')),
                    ],
                    onChanged: (val) {
                      if (val != null) setModalState(() => reminderType = val);
                    },
                  ),
                  const Spacer(),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.calendar_today, size: 16),
                    label: Text(
                      '${selectedDate.year}-${selectedDate.month.toString().padLeft(2, '0')}-${selectedDate.day.toString().padLeft(2, '0')}',
                    ),
                    onPressed: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: selectedDate,
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (picked != null) {
                        setModalState(() => selectedDate = picked);
                      }
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                    ),
                    onPressed: () async {
                      final title = titleController.text.trim();
                      if (title.isEmpty) return;
                      Navigator.pop(ctx);
                      try {
                        final created = await widget.reminderService.createReminder(
                          title: title,
                          description: descController.text.trim().isNotEmpty
                              ? descController.text.trim()
                              : null,
                          dueDate: selectedDate,
                          reminderType: reminderType,
                        );
                        setState(() => _reminders.insert(0, created));
                      } catch (e) {
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Failed to create reminder: $e')),
                        );
                      }
                    },
                    child: const Text('Save Reminder', style: TextStyle(color: Colors.white)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts & Reminders', style: TextStyle(fontWeight: FontWeight.bold)),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.primaryColor,
          labelColor: AppTheme.primaryColor,
          unselectedLabelColor: Colors.grey.shade600,
          tabs: const [
            Tab(icon: Icon(Icons.notifications_outlined), text: 'Notifications'),
            Tab(icon: Icon(Icons.alarm_outlined), text: 'Reminders'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all),
            tooltip: 'Mark All Read',
            onPressed: _notifications.any((n) => !n.isRead) ? _markAllRead : null,
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildNotificationsTab(),
          _buildRemindersTab(),
        ],
      ),
      floatingActionButton: _tabController.index == 1
          ? FloatingActionButton(
              backgroundColor: AppTheme.primaryColor,
              onPressed: _showCreateReminderDialog,
              child: const Icon(Icons.add, color: Colors.white),
            )
          : null,
    );
  }

  Widget _buildNotificationsTab() {
    if (_isLoadingNotifications) {
      return const LoadingView(message: 'Loading notifications...');
    }
    if (_notificationsError != null) {
      return ErrorStateView(
        message: _notificationsError!,
        onRetry: _loadNotifications,
      );
    }
    if (_notifications.isEmpty) {
      return EmptyStateView(
        icon: Icons.notifications_none,
        title: 'All Caught Up!',
        message: 'No notifications at this time. Application updates and interview alerts will appear here.',
        actionLabel: 'Refresh',
        onAction: _loadNotifications,
      );
    }

    return RefreshIndicator(
      onRefresh: _loadNotifications,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: _notifications.length,
        itemBuilder: (context, index) {
          final item = _notifications[index];
          return _buildNotificationCard(item);
        },
      ),
    );
  }

  Widget _buildNotificationCard(NotificationItem item) {
    IconData icon;
    Color iconColor;

    switch (item.notificationType) {
      case 'interview':
        icon = Icons.celebration;
        iconColor = Colors.purple;
        break;
      case 'deadline':
        icon = Icons.alarm;
        iconColor = Colors.red.shade700;
        break;
      case 'application_update':
        icon = Icons.work;
        iconColor = AppTheme.primaryColor;
        break;
      case 'follow_up':
        icon = Icons.reply;
        iconColor = Colors.teal;
        break;
      default:
        icon = Icons.notifications;
        iconColor = Colors.blueGrey;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: item.isRead ? 0.5 : 2,
      color: item.isRead ? Colors.white : Colors.blue.shade50.withOpacity(0.4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: iconColor.withOpacity(0.12),
          child: Icon(icon, color: iconColor, size: 22),
        ),
        title: Text(
          item.title,
          style: TextStyle(
            fontWeight: item.isRead ? FontWeight.w500 : FontWeight.bold,
            fontSize: 14,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 3),
            Text(item.message, style: TextStyle(fontSize: 12, color: Colors.grey.shade800)),
            const SizedBox(height: 4),
            Text(
              '${item.createdAt.year}-${item.createdAt.month.toString().padLeft(2, '0')}-${item.createdAt.day.toString().padLeft(2, '0')}',
              style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
            ),
          ],
        ),
        trailing: IconButton(
          icon: const Icon(Icons.close, size: 18, color: Colors.grey),
          tooltip: 'Dismiss Notification',
          onPressed: () => _deleteNotification(item.id),
        ),
        onTap: () => _markAsRead(item),
      ),
    );
  }

  Widget _buildRemindersTab() {
    return Column(
      children: [
        // Filter Chips
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  label: const Text('All'),
                  selected: _selectedReminderStatus == null,
                  onSelected: (_) {
                    setState(() => _selectedReminderStatus = null);
                    _loadReminders();
                  },
                ),
                const SizedBox(width: 6),
                FilterChip(
                  label: const Text('Active'),
                  selected: _selectedReminderStatus == 'active',
                  onSelected: (val) {
                    setState(() => _selectedReminderStatus = val ? 'active' : null);
                    _loadReminders();
                  },
                ),
                const SizedBox(width: 6),
                FilterChip(
                  label: const Text('Overdue'),
                  selected: _selectedReminderStatus == 'overdue',
                  onSelected: (val) {
                    setState(() => _selectedReminderStatus = val ? 'overdue' : null);
                    _loadReminders();
                  },
                ),
                const SizedBox(width: 6),
                FilterChip(
                  label: const Text('Completed'),
                  selected: _selectedReminderStatus == 'completed',
                  onSelected: (val) {
                    setState(() => _selectedReminderStatus = val ? 'completed' : null);
                    _loadReminders();
                  },
                ),
              ],
            ),
          ),
        ),

        Expanded(
          child: _isLoadingReminders
              ? const LoadingView(message: 'Loading reminders...')
              : _remindersError != null
                  ? ErrorStateView(
                      message: _remindersError!,
                      onRetry: _loadReminders,
                    )
                  : _reminders.isEmpty
                      ? EmptyStateView(
                          icon: Icons.alarm_off_outlined,
                          title: 'No Reminders',
                          message: 'Create configurable reminders for interview follow-ups and deadlines.',
                          actionLabel: 'Create Reminder',
                          onAction: _showCreateReminderDialog,
                        )
                      : RefreshIndicator(
                          onRefresh: _loadReminders,
                          child: ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            itemCount: _reminders.length,
                            itemBuilder: (context, index) {
                              final item = _reminders[index];
                              return _buildReminderCard(item);
                            },
                          ),
                        ),
        ),
      ],
    );
  }

  Widget _buildReminderCard(ReminderItem item) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Checkbox(
              value: item.isCompleted,
              activeColor: AppTheme.accentColor,
              onChanged: (val) {
                if (val == true) {
                  _completeReminder(item);
                }
              },
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          item.title,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            decoration: item.isCompleted
                                ? TextDecoration.lineThrough
                                : null,
                          ),
                        ),
                      ),
                      if (item.isOverdue) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.red.shade100,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'OVERDUE',
                            style: TextStyle(
                              color: Colors.red.shade900,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (item.description != null && item.description!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      item.description!,
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Icon(Icons.event, size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        'Due: ${item.dueDate.year}-${item.dueDate.month.toString().padLeft(2, '0')}-${item.dueDate.day.toString().padLeft(2, '0')}',
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade200,
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: Text(
                          item.reminderType.toUpperCase(),
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, size: 18),
              onSelected: (val) {
                if (val == 'dismiss') {
                  _dismissReminder(item);
                } else if (val == 'delete') {
                  _deleteReminder(item.id);
                }
              },
              itemBuilder: (ctx) => [
                const PopupMenuItem(value: 'dismiss', child: Text('Dismiss')),
                const PopupMenuItem(value: 'delete', child: Text('Delete')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
