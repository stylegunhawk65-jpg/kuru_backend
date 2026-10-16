import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kuru_app/core/api/api_client.dart';
import 'package:kuru_app/core/storage/token_storage.dart';
import 'package:kuru_app/models/notification_item.dart';
import 'package:kuru_app/models/reminder_item.dart';
import 'package:kuru_app/screens/login_screen.dart';
import 'package:kuru_app/screens/notifications_screen.dart';
import 'package:kuru_app/screens/widgets/agent_step_timeline.dart';
import 'package:kuru_app/screens/widgets/state_views.dart';
import 'package:kuru_app/services/auth_service.dart';
import 'package:kuru_app/services/notification_service.dart';
import 'package:kuru_app/services/reminder_service.dart';

void main() {
  testWidgets('LoginScreen renders brand title and quick login button', (WidgetTester tester) async {
    final storage = TokenStorage();
    final authService = AuthService(storage: storage);

    await tester.pumpWidget(MaterialApp(
      home: LoginScreen(authService: authService),
    ));
    await tester.pump();

    // Verify Brand title is rendered
    expect(find.text('Kuru Career Twin'), findsOneWidget);
    expect(find.text('Enter Career Twin Workspace'), findsOneWidget);
  });

  testWidgets('AgentStepTimeline renders all 9 agents with proper titles', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AgentStepTimeline(
              completedSteps: ['career_profile', 'github_analysis'],
              currentRunningStep: 'job_matching',
            ),
          ),
        ),
      ),
    );

    // Verify logical agent step titles
    expect(find.text('1. Career Profile Agent'), findsOneWidget);
    expect(find.text('2. GitHub Analysis Agent'), findsOneWidget);
    expect(find.text('3. Job Matching Agent'), findsOneWidget);
    expect(find.text('4. Skill Gap Agent'), findsOneWidget);
    expect(find.text('5. Career Planning Agent'), findsOneWidget);
    expect(find.text('6. Resource Research Agent'), findsOneWidget);
    expect(find.text('7. Project Recommendation Agent'), findsOneWidget);
    expect(find.text('8. Resume Agent'), findsOneWidget);
    expect(find.text('9. Approval Workflow Agent'), findsOneWidget);
  });

  testWidgets('StateViews render loading and empty states properly', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              LoadingView(message: 'Loading test items...'),
              EmptyStateView(
                icon: Icons.inbox,
                title: 'Empty Inbox',
                message: 'No messages found.',
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Loading test items...'), findsOneWidget);
    expect(find.text('Empty Inbox'), findsOneWidget);
    expect(find.text('No messages found.'), findsOneWidget);
  });

  testWidgets('NotificationsScreen renders notifications list and reminder tabs', (WidgetTester tester) async {
    final notifService = _TestNotificationService();
    final reminderService = _TestReminderService();

    await tester.pumpWidget(MaterialApp(
      home: NotificationsScreen(
        notificationService: notifService,
        reminderService: reminderService,
      ),
    ));
    await tester.pumpAndSettle();

    // Verify screen title and tabs
    expect(find.text('Alerts & Reminders'), findsOneWidget);
    expect(find.text('Notifications'), findsOneWidget);
    expect(find.text('Reminders'), findsOneWidget);

    // Verify mock notification item rendered
    expect(find.text('Interview Stage Reached!'), findsOneWidget);
    expect(find.text('Your application for Razorpay is in interview stage.'), findsOneWidget);

    // Switch to Reminders tab
    await tester.tap(find.text('Reminders'));
    await tester.pumpAndSettle();

    // Verify mock reminder item rendered
    expect(find.text('Submit take-home task'), findsOneWidget);
  });
}

class _TestNotificationService extends NotificationService {
  _TestNotificationService() : super(ApiClient(storage: TokenStorage()));

  @override
  Future<List<NotificationItem>> getNotifications({
    bool? isRead,
    String? notificationType,
    int limit = 50,
    int offset = 0,
  }) async {
    return [
      NotificationItem(
        id: 'notif_test_1',
        firebaseUid: 'test_uid',
        title: 'Interview Stage Reached!',
        message: 'Your application for Razorpay is in interview stage.',
        notificationType: 'interview',
        isRead: false,
        data: {},
        createdAt: DateTime(2026, 10, 17),
        updatedAt: DateTime(2026, 10, 17),
      ),
    ];
  }

  @override
  Future<int> getUnreadCount() async => 1;
}

class _TestReminderService extends ReminderService {
  _TestReminderService() : super(ApiClient(storage: TokenStorage()));

  @override
  Future<List<ReminderItem>> getReminders({
    String? status,
    String? jobId,
  }) async {
    return [
      ReminderItem(
        id: 'rem_test_1',
        firebaseUid: 'test_uid',
        title: 'Submit take-home task',
        description: 'Complete coding challenge',
        dueDate: DateTime(2026, 10, 20),
        reminderType: 'deadline',
        isCompleted: false,
        isDismissed: false,
        isOverdue: false,
        createdAt: DateTime(2026, 10, 16),
        updatedAt: DateTime(2026, 10, 16),
      ),
    ];
  }
}
