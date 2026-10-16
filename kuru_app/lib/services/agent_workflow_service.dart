import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/agent_workflow.dart';

/// Service coordinating LangGraph 9-agent workflows and human-in-the-loop approvals.
class AgentWorkflowService {
  final ApiClient _client;

  AgentWorkflowService(this._client);

  /// Trigger the complete 9-agent Career Twin pipeline
  Future<Map<String, dynamic>> runFullCareerTwin({
    String? targetRole,
    String? targetJobId,
    int weeklyHours = 12,
    String? actionToQueue,
  }) async {
    final payload = {
      if (targetRole != null && targetRole.isNotEmpty) 'target_role': targetRole,
      'target_job_id': ?targetJobId,
      'weekly_hours': weeklyHours,
      'action_to_queue': ?actionToQueue,
    };
    final res = await _client.post(ApiConfig.agentsFullWorkflowEndpoint, body: payload);
    return (res as Map<String, dynamic>?) ?? {};
  }

  /// Trigger the focused roadmap & projects subworkflow
  Future<Map<String, dynamic>> runRoadmapSubworkflow({
    required String targetRole,
    int weeklyHours = 12,
  }) async {
    final payload = {
      'target_role': targetRole,
      'weekly_hours': weeklyHours,
    };
    final res = await _client.post(ApiConfig.agentsRoadmapWorkflowEndpoint, body: payload);
    return (res as Map<String, dynamic>?) ?? {};
  }

  /// Fetch pending human approval requests
  Future<List<AgentApprovalRequest>> getPendingApprovals() async {
    final res = await _client.get(ApiConfig.agentsApprovalsEndpoint);
    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('approvals')) {
      items = res['approvals'] as List<dynamic>;
    }
    return items.map((e) => AgentApprovalRequest.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Submit human decision (approve or reject) for a consequential agent action
  Future<Map<String, dynamic>> submitApprovalDecision({
    required int approvalId,
    required bool approved,
    String? feedback,
  }) async {
    final payload = {
      'approved': approved,
      'feedback': ?feedback,
    };
    final res = await _client.post(
      '${ApiConfig.agentsApprovalsEndpoint}/$approvalId/decision',
      body: payload,
    );
    return (res as Map<String, dynamic>?) ?? {};
  }
}
