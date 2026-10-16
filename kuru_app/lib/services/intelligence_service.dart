import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/skill_gap.dart';

/// Service managing Career Intelligence, prioritized skill gaps, and What-If simulations.
class IntelligenceService {
  final ApiClient _client;

  IntelligenceService(this._client);

  /// Fetch prioritized skill gaps
  Future<List<PrioritizedSkillGap>> getSkillGaps({String? targetRole}) async {
    final params = <String, dynamic>{
      if (targetRole != null && targetRole.isNotEmpty) 'target_role': targetRole,
    };
    final res = await _client.get(ApiConfig.intelligenceGapsEndpoint, queryParams: params);

    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('gaps')) {
      items = res['gaps'] as List<dynamic>;
    } else if (res is Map && res.containsKey('prioritized_gaps')) {
      items = res['prioritized_gaps'] as List<dynamic>;
    }
    return items.map((e) => PrioritizedSkillGap.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Run deterministic What-If career simulator
  Future<WhatIfSimulationResult> simulateCareerPath({
    required String targetRole,
    required List<String> simulatedSkills,
  }) async {
    final payload = {
      'target_role': targetRole,
      'simulated_skills': simulatedSkills,
    };
    final res = await _client.post(ApiConfig.intelligenceSimulateEndpoint, body: payload);
    return WhatIfSimulationResult.fromJson(res as Map<String, dynamic>);
  }
}
