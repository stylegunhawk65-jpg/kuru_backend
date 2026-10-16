import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../services/agent_workflow_service.dart';
import '../services/application_service.dart';
import '../services/auth_service.dart';
import '../services/firestore_service.dart';
import '../services/github_service.dart';
import '../services/intelligence_service.dart';
import '../services/jobs_service.dart';
import '../services/notification_service.dart';
import '../services/profile_service.dart';
import '../services/reminder_service.dart';
import '../services/resume_service.dart';
import 'approvals_screen.dart';
import 'career_twin_screen.dart';
import 'jobs_screen.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';
import 'resume_screen.dart';
import 'skill_gaps_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  final ProfileService profileService;
  final GithubService githubService;
  final JobsService jobsService;
  final IntelligenceService intelligenceService;
  final AgentWorkflowService workflowService;
  final AuthService authService;
  final FirestoreService? firestoreService;
  final ResumeService? resumeService;
  final ApplicationService? applicationService;
  final NotificationService? notificationService;
  final ReminderService? reminderService;

  const MainNavigationScreen({
    super.key,
    required this.profileService,
    required this.githubService,
    required this.jobsService,
    required this.intelligenceService,
    required this.workflowService,
    required this.authService,
    this.firestoreService,
    this.resumeService,
    this.applicationService,
    this.notificationService,
    this.reminderService,
  });

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      CareerTwinScreen(workflowService: widget.workflowService),
      JobsScreen(
        jobsService: widget.jobsService,
        applicationService: widget.applicationService,
        resumeService: widget.resumeService,
      ),
      SkillGapsScreen(
        githubService: widget.githubService,
        intelligenceService: widget.intelligenceService,
      ),
      if (widget.resumeService != null)
        ResumeScreen(resumeService: widget.resumeService!),
      ApprovalsScreen(workflowService: widget.workflowService),
      if (widget.notificationService != null && widget.reminderService != null)
        NotificationsScreen(
          notificationService: widget.notificationService!,
          reminderService: widget.reminderService!,
        ),
      ProfileScreen(
        profileService: widget.profileService,
        githubService: widget.githubService,
        authService: widget.authService,
        firestoreService: widget.firestoreService,
      ),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
        indicatorColor: AppTheme.primaryColor.withOpacity(0.15),
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.psychology_outlined),
            selectedIcon: Icon(Icons.psychology, color: AppTheme.primaryColor),
            label: 'Twin',
          ),
          const NavigationDestination(
            icon: Icon(Icons.work_outline),
            selectedIcon: Icon(Icons.work, color: AppTheme.primaryColor),
            label: 'Jobs',
          ),
          const NavigationDestination(
            icon: Icon(Icons.trending_up_outlined),
            selectedIcon: Icon(Icons.trending_up, color: AppTheme.primaryColor),
            label: 'Skill Gaps',
          ),
          if (widget.resumeService != null)
            const NavigationDestination(
              icon: Icon(Icons.description_outlined),
              selectedIcon: Icon(Icons.description, color: AppTheme.primaryColor),
              label: 'Resumes',
            ),
          const NavigationDestination(
            icon: Icon(Icons.verified_user_outlined),
            selectedIcon: Icon(Icons.verified_user, color: AppTheme.primaryColor),
            label: 'Approvals',
          ),
          if (widget.notificationService != null && widget.reminderService != null)
            const NavigationDestination(
              icon: Icon(Icons.notifications_outlined),
              selectedIcon: Icon(Icons.notifications, color: AppTheme.primaryColor),
              label: 'Alerts',
            ),
          const NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person, color: AppTheme.primaryColor),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
