import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kuru_app/core/storage/token_storage.dart';
import 'package:kuru_app/screens/login_screen.dart';
import 'package:kuru_app/screens/widgets/agent_step_timeline.dart';
import 'package:kuru_app/screens/widgets/state_views.dart';
import 'package:kuru_app/services/auth_service.dart';

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
}
