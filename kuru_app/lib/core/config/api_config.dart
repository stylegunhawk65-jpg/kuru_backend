import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

/// Environment configuration and API endpoint discovery for Kuru Backend.
class ApiConfig {
  static const String appName = 'Kuru Career Twin';
  static const String appVersion = '0.1.0';

  // Firebase Project Configuration
  static const String firebaseProjectId = 'career-ba46c';

  // Default API Hosts
  static const String androidEmulatorHost = 'http://10.0.2.2:8000';
  static const String localhostHost = 'http://127.0.0.1:8000';
  static const String defaultApiPrefix = '/api/v1';

  // Runtime configurable base URL
  static String? _customBaseUrl;

  /// Set a custom base URL (e.g. for physical devices on local Wi-Fi: http://192.168.1.50:8000/api/v1)
  static void setCustomBaseUrl(String? url) {
    if (url != null && url.isNotEmpty) {
      _customBaseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    } else {
      _customBaseUrl = null;
    }
  }

  /// Automatically resolves the correct backend host based on the runtime platform.
  static String get defaultHost {
    if (kIsWeb) {
      return localhostHost;
    }
    try {
      if (Platform.isAndroid) {
        // Android Emulator loops back to host machine on 10.0.2.2
        return androidEmulatorHost;
      }
    } catch (_) {
      // Fallback if Platform is unsupported
    }
    return localhostHost;
  }

  /// Returns the complete base API URL (e.g. "http://10.0.2.2:8000/api/v1")
  static String get apiBaseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }
    return '$defaultHost$defaultApiPrefix';
  }

  // Endpoints
  static String get healthEndpoint => '$apiBaseUrl/health';
  static String get observabilityEndpoint => '$apiBaseUrl/health/observability';
  static String get profilesEndpoint => '$apiBaseUrl/profiles';
  static String get myProfileEndpoint => '$apiBaseUrl/profiles/me';
  static String get githubConnectEndpoint => '$apiBaseUrl/github/connect';
  static String get githubStatusEndpoint => '$apiBaseUrl/github/status';
  static String get githubAnalyzeEndpoint => '$apiBaseUrl/github/analyze';
  static String get skillsEndpoint => '$apiBaseUrl/github/skills';
  static String get skillGraphEndpoint => '$apiBaseUrl/github/graph';
  static String get jobsEndpoint => '$apiBaseUrl/jobs';
  static String get savedJobsEndpoint => '$apiBaseUrl/jobs/saved';
  static String get intelligenceAssessmentEndpoint => '$apiBaseUrl/intelligence/assessment';
  static String get intelligenceGapsEndpoint => '$apiBaseUrl/intelligence/gaps';
  static String get intelligenceRecommendationsEndpoint => '$apiBaseUrl/intelligence/recommendations';
  static String get intelligenceSimulateEndpoint => '$apiBaseUrl/intelligence/simulate';
  static String get agentsFullWorkflowEndpoint => '$apiBaseUrl/agents/workflow/full';
  static String get agentsRoadmapWorkflowEndpoint => '$apiBaseUrl/agents/workflow/roadmap';
  static String get agentsApprovalsEndpoint => '$apiBaseUrl/agents/approvals';
  static String get resumesEndpoint => '$apiBaseUrl/resumes';
  static String get applicationsEndpoint => '$apiBaseUrl/applications';
  static String get notificationsEndpoint => '$apiBaseUrl/notifications';
  static String get remindersEndpoint => '$apiBaseUrl/reminders';

  // Request timeout duration
  static const Duration requestTimeout = Duration(seconds: 45);
}
