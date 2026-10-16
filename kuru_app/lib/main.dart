import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'core/api/api_client.dart';
import 'core/config/api_config.dart';
import 'core/storage/token_storage.dart';
import 'core/theme/app_theme.dart';
import 'firebase_options.dart';
import 'screens/login_screen.dart';
import 'screens/main_navigation_screen.dart';
import 'services/agent_workflow_service.dart';
import 'services/application_service.dart';
import 'services/auth_service.dart';
import 'services/firestore_service.dart';
import 'services/github_service.dart';
import 'services/intelligence_service.dart';
import 'services/jobs_service.dart';
import 'services/profile_service.dart';
import 'services/resume_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Initialize Firebase using DefaultFirebaseOptions (configured with google-services.json)
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    debugPrint('Firebase.initializeApp notice (fallback enabled for tests/mock env): $e');
  }

  // 2. Initialize persistent token cache
  final tokenStorage = TokenStorage();
  await tokenStorage.init();

  // 3. Initialize Authentication Service (Firebase Auth integration)
  final authService = AuthService(storage: tokenStorage);

  // 4. Initialize Cloud Firestore Service
  final firestoreService = FirestoreService(authService: authService);

  // 5. Initialize ApiClient with Bearer token injection, token refresh provider, & 401 handler
  final apiClient = ApiClient(
    storage: tokenStorage,
    tokenProvider: () async => await authService.getIdToken(),
    onAuthExpired: () {
      authService.handleAuthExpired();
    },
  );

  // 6. Instantiate API feature services
  final profileService = ProfileService(apiClient);
  final githubService = GithubService(apiClient);
  final jobsService = JobsService(apiClient);
  final intelligenceService = IntelligenceService(apiClient);
  final workflowService = AgentWorkflowService(apiClient);
  final resumeService = ResumeService(apiClient);
  final applicationService = ApplicationService(apiClient);

  runApp(KuruApp(
    authService: authService,
    firestoreService: firestoreService,
    profileService: profileService,
    githubService: githubService,
    jobsService: jobsService,
    intelligenceService: intelligenceService,
    workflowService: workflowService,
    resumeService: resumeService,
    applicationService: applicationService,
  ));
}

class KuruApp extends StatelessWidget {
  final AuthService authService;
  final FirestoreService firestoreService;
  final ProfileService profileService;
  final GithubService githubService;
  final JobsService jobsService;
  final IntelligenceService intelligenceService;
  final AgentWorkflowService workflowService;
  final ResumeService? resumeService;
  final ApplicationService? applicationService;

  const KuruApp({
    super.key,
    required this.authService,
    required this.firestoreService,
    required this.profileService,
    required this.githubService,
    required this.jobsService,
    required this.intelligenceService,
    required this.workflowService,
    this.resumeService,
    this.applicationService,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: authService,
      builder: (context, _) {
        final isAuthenticated = authService.isAuthenticated;

        return MaterialApp(
          title: ApiConfig.appName,
          theme: AppTheme.lightTheme,
          darkTheme: AppTheme.darkTheme,
          themeMode: ThemeMode.system,
          debugShowCheckedModeBanner: false,
          home: isAuthenticated
              ? MainNavigationScreen(
                  profileService: profileService,
                  githubService: githubService,
                  jobsService: jobsService,
                  intelligenceService: intelligenceService,
                  workflowService: workflowService,
                  authService: authService,
                  firestoreService: firestoreService,
                  resumeService: resumeService,
                  applicationService: applicationService,
                )
              : LoginScreen(authService: authService),
        );
      },
    );
  }
}
