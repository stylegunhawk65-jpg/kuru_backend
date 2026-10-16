import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/skill_gap.dart';

/// Service managing GitHub OAuth, repo analysis, and evidence-backed skill extraction.
class GithubService {
  final ApiClient _client;

  GithubService(this._client);

  /// Get current GitHub connection status
  Future<Map<String, dynamic>> getStatus() async {
    final res = await _client.get(ApiConfig.githubStatusEndpoint);
    return (res as Map<String, dynamic>?) ?? {};
  }

  /// Connect GitHub account using token
  Future<Map<String, dynamic>> connect({required String personalAccessToken}) async {
    final payload = {'access_token': personalAccessToken};
    final res = await _client.post(ApiConfig.githubConnectEndpoint, body: payload);
    return (res as Map<String, dynamic>?) ?? {};
  }

  /// Trigger repository code analysis
  Future<Map<String, dynamic>> triggerAnalysis({List<String>? selectedRepos}) async {
    final payload = {
      'repository_names': ?selectedRepos,
    };
    final res = await _client.post(ApiConfig.githubAnalyzeEndpoint, body: payload);
    return (res as Map<String, dynamic>?) ?? {};
  }

  /// Get verified evidence-backed skills extracted from GitHub
  Future<List<StudentSkill>> getSkills() async {
    final res = await _client.get(ApiConfig.skillsEndpoint);
    if (res is List) {
      return res.map((item) => StudentSkill.fromJson(item as Map<String, dynamic>)).toList();
    } else if (res is Map && res.containsKey('skills')) {
      final list = res['skills'] as List<dynamic>;
      return list.map((item) => StudentSkill.fromJson(item as Map<String, dynamic>)).toList();
    }
    return [];
  }

  /// Get the Skill Graph relations and edges
  Future<Map<String, dynamic>> getSkillGraph() async {
    final res = await _client.get(ApiConfig.skillGraphEndpoint);
    return (res as Map<String, dynamic>?) ?? {};
  }
}
