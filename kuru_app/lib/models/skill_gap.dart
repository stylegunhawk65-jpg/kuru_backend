library;

/// Skill and Skill-Gap models corresponding to Phase 3 & Phase 5 FastAPI schemas.

class StudentSkill {
  final String skillName;
  final String category;
  final String evidenceLevel; // strong, moderate, baseline
  final double confidenceScore;
  final List<String> sourceRepositories;

  StudentSkill({
    required this.skillName,
    this.category = 'General',
    this.evidenceLevel = 'moderate',
    this.confidenceScore = 0.8,
    this.sourceRepositories = const [],
  });

  factory StudentSkill.fromJson(Map<String, dynamic> json) {
    return StudentSkill(
      skillName: (json['skill_name'] ?? json['name'] ?? '') as String,
      category: (json['category'] ?? 'General') as String,
      evidenceLevel: (json['evidence_level'] ?? json['level'] ?? 'moderate') as String,
      confidenceScore: (json['confidence_score'] ?? json['confidence'] ?? 0.8 as num).toDouble(),
      sourceRepositories: (json['source_repositories'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'skill_name': skillName,
      'category': category,
      'evidence_level': evidenceLevel,
      'confidence_score': confidenceScore,
      'source_repositories': sourceRepositories,
    };
  }
}

class PrioritizedSkillGap {
  final String skillName;
  final String category;
  final int demandFrequency;
  final String urgency; // high, medium, low
  final String rationale;

  PrioritizedSkillGap({
    required this.skillName,
    this.category = 'General',
    this.demandFrequency = 1,
    this.urgency = 'high',
    this.rationale = '',
  });

  factory PrioritizedSkillGap.fromJson(Map<String, dynamic> json) {
    return PrioritizedSkillGap(
      skillName: (json['skill_name'] ?? json['name'] ?? '') as String,
      category: (json['category'] ?? 'General') as String,
      demandFrequency: (json['demand_frequency'] ?? json['market_demand'] ?? 1) as int,
      urgency: (json['urgency'] ?? 'medium') as String,
      rationale: (json['rationale'] ?? json['reason'] ?? '') as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'skill_name': skillName,
      'category': category,
      'demand_frequency': demandFrequency,
      'urgency': urgency,
      'rationale': rationale,
    };
  }
}

class WhatIfSimulationResult {
  final String targetRole;
  final double baselineScore;
  final double projectedScore;
  final double scoreLift;
  final int newlyEligibleJobsCount;
  final List<String> simulatedSkills;
  final List<String> fastestPathSkills;

  WhatIfSimulationResult({
    required this.targetRole,
    required this.baselineScore,
    required this.projectedScore,
    required this.scoreLift,
    required this.newlyEligibleJobsCount,
    this.simulatedSkills = const [],
    this.fastestPathSkills = const [],
  });

  factory WhatIfSimulationResult.fromJson(Map<String, dynamic> json) {
    return WhatIfSimulationResult(
      targetRole: (json['target_role'] ?? 'Target Role') as String,
      baselineScore: ((json['baseline_score'] ?? json['current_score'] ?? 0.0) as num).toDouble(),
      projectedScore: ((json['projected_score'] ?? json['simulated_score'] ?? 0.0) as num).toDouble(),
      scoreLift: ((json['score_lift'] ?? json['lift'] ?? 0.0) as num).toDouble(),
      newlyEligibleJobsCount: (json['newly_eligible_jobs_count'] ?? json['eligible_jobs'] ?? 0) as int,
      simulatedSkills: (json['simulated_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      fastestPathSkills: (json['fastest_path_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
    );
  }
}
