library;

/// Models representing LangGraph multi-agent orchestration states, roadmaps, and approvals.

class AgentWorkflowRun {
  final String id;
  final String workflowType;
  final String status; // running, waiting_approval, completed, failed
  final String currentStep;
  final Map<String, dynamic> stateSummary;
  final String? errorMessage;
  final DateTime? createdAt;

  AgentWorkflowRun({
    required this.id,
    required this.workflowType,
    required this.status,
    required this.currentStep,
    this.stateSummary = const {},
    this.errorMessage,
    this.createdAt,
  });

  factory AgentWorkflowRun.fromJson(Map<String, dynamic> json) {
    return AgentWorkflowRun(
      id: (json['id'] ?? json['run_id'] ?? '').toString(),
      workflowType: (json['workflow_type'] ?? 'full_career_twin') as String,
      status: (json['status'] ?? 'completed') as String,
      currentStep: (json['current_step'] ?? 'end') as String,
      stateSummary: (json['state_summary'] as Map<String, dynamic>?) ?? {},
      errorMessage: json['error_message'] as String?,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
    );
  }
}

class AgentApprovalRequest {
  final int id;
  final String actionType;
  final String status; // pending, approved, rejected, executed
  final String actionDescription;
  final Map<String, dynamic> payload;
  final DateTime? createdAt;

  AgentApprovalRequest({
    required this.id,
    required this.actionType,
    required this.status,
    required this.actionDescription,
    this.payload = const {},
    this.createdAt,
  });

  factory AgentApprovalRequest.fromJson(Map<String, dynamic> json) {
    return AgentApprovalRequest(
      id: (json['id'] ?? 0) as int,
      actionType: (json['action_type'] ?? 'submit_application') as String,
      status: (json['status'] ?? 'pending') as String,
      actionDescription: (json['action_description'] ?? 'Consequential action queued for review.') as String,
      payload: (json['payload'] as Map<String, dynamic>?) ?? {},
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
    );
  }
}

class RoadmapMilestone {
  final int weekNumber;
  final String title;
  final String description;
  final List<String> focusSkills;
  final int estimatedHours;

  RoadmapMilestone({
    required this.weekNumber,
    required this.title,
    required this.description,
    this.focusSkills = const [],
    this.estimatedHours = 12,
  });

  factory RoadmapMilestone.fromJson(Map<String, dynamic> json) {
    return RoadmapMilestone(
      weekNumber: (json['week_number'] ?? json['week'] ?? 1) as int,
      title: (json['title'] ?? 'Learning Milestone') as String,
      description: (json['description'] ?? '') as String,
      focusSkills: (json['focus_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      estimatedHours: (json['estimated_hours'] ?? 12) as int,
    );
  }
}

class RecommendedProject {
  final String title;
  final String description;
  final List<String> targetSkills;
  final String difficulty; // beginner, intermediate, advanced
  final String architectureHint;

  RecommendedProject({
    required this.title,
    required this.description,
    this.targetSkills = const [],
    this.difficulty = 'intermediate',
    this.architectureHint = '',
  });

  factory RecommendedProject.fromJson(Map<String, dynamic> json) {
    return RecommendedProject(
      title: (json['title'] ?? 'Career Portfolio Project') as String,
      description: (json['description'] ?? '') as String,
      targetSkills: (json['target_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      difficulty: (json['difficulty'] ?? 'intermediate') as String,
      architectureHint: (json['architecture_hint'] ?? json['hint'] ?? '') as String,
    );
  }
}

class LearningResource {
  final String title;
  final String url;
  final String type; // documentation, tutorial, course
  final String provider;

  LearningResource({
    required this.title,
    required this.url,
    required this.type,
    required this.provider,
  });

  factory LearningResource.fromJson(Map<String, dynamic> json) {
    return LearningResource(
      title: (json['title'] ?? 'Documentation') as String,
      url: (json['url'] ?? '') as String,
      type: (json['type'] ?? 'official_docs') as String,
      provider: (json['provider'] ?? 'Official') as String,
    );
  }
}
