/// Models representing ATS-friendly resumes and evidence citations.

class ResumeContactInfo {
  final String name;
  final String email;
  final String? phone;
  final String? github;
  final String? linkedin;
  final String? location;
  final String? portfolio;

  ResumeContactInfo({
    required this.name,
    required this.email,
    this.phone,
    this.github,
    this.linkedin,
    this.location,
    this.portfolio,
  });

  factory ResumeContactInfo.fromJson(Map<String, dynamic> json) {
    return ResumeContactInfo(
      name: (json['name'] ?? 'Candidate') as String,
      email: (json['email'] ?? '') as String,
      phone: json['phone'] as String?,
      github: json['github'] as String?,
      linkedin: json['linkedin'] as String?,
      location: json['location'] as String?,
      portfolio: json['portfolio'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'email': email,
      'phone': phone,
      'github': github,
      'linkedin': linkedin,
      'location': location,
      'portfolio': portfolio,
    };
  }
}

class ResumeSkillItem {
  final String name;
  final String category;
  final List<String> evidencePaths;
  final String? proficiencyLevel;
  final double? assessmentScore;

  ResumeSkillItem({
    required this.name,
    this.category = 'General',
    this.evidencePaths = const [],
    this.proficiencyLevel,
    this.assessmentScore,
  });

  factory ResumeSkillItem.fromJson(Map<String, dynamic> json) {
    return ResumeSkillItem(
      name: (json['name'] ?? '') as String,
      category: (json['category'] ?? 'General') as String,
      evidencePaths: (json['evidence_paths'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      proficiencyLevel: json['proficiency_level'] as String?,
      assessmentScore: json['assessment_score'] != null ? (json['assessment_score'] as num).toDouble() : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'category': category,
      'evidence_paths': evidencePaths,
      'proficiency_level': proficiencyLevel,
      'assessment_score': assessmentScore,
    };
  }
}

class ResumeProjectItem {
  final String title;
  final String? repoName;
  final String? summary;
  final List<String> bullets;
  final List<String> technologies;
  final String? githubUrl;

  ResumeProjectItem({
    required this.title,
    this.repoName,
    this.summary,
    this.bullets = const [],
    this.technologies = const [],
    this.githubUrl,
  });

  factory ResumeProjectItem.fromJson(Map<String, dynamic> json) {
    return ResumeProjectItem(
      title: (json['title'] ?? '') as String,
      repoName: json['repo_name'] as String?,
      summary: json['summary'] as String?,
      bullets: (json['bullets'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      technologies: (json['technologies'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      githubUrl: json['github_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'repo_name': repoName,
      'summary': summary,
      'bullets': bullets,
      'technologies': technologies,
      'github_url': githubUrl,
    };
  }
}

class ResumeExperienceItem {
  final String company;
  final String role;
  final String? startDate;
  final String? endDate;
  final List<String> bullets;

  ResumeExperienceItem({
    required this.company,
    required this.role,
    this.startDate,
    this.endDate,
    this.bullets = const [],
  });

  factory ResumeExperienceItem.fromJson(Map<String, dynamic> json) {
    return ResumeExperienceItem(
      company: (json['company'] ?? '') as String,
      role: (json['role'] ?? '') as String,
      startDate: json['start_date'] as String?,
      endDate: json['end_date'] as String?,
      bullets: (json['bullets'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'company': company,
      'role': role,
      'start_date': startDate,
      'end_date': endDate,
      'bullets': bullets,
    };
  }
}

class ResumeEducationItem {
  final String institution;
  final String degree;
  final int? graduationYear;
  final String? fieldOfStudy;

  ResumeEducationItem({
    required this.institution,
    required this.degree,
    this.graduationYear,
    this.fieldOfStudy,
  });

  factory ResumeEducationItem.fromJson(Map<String, dynamic> json) {
    return ResumeEducationItem(
      institution: (json['institution'] ?? '') as String,
      degree: (json['degree'] ?? '') as String,
      graduationYear: json['graduation_year'] as int?,
      fieldOfStudy: json['field_of_study'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'institution': institution,
      'degree': degree,
      'graduation_year': graduationYear,
      'field_of_study': fieldOfStudy,
    };
  }
}

class ResumeAssessmentItem {
  final String skillName;
  final double score;
  final String level;
  final bool passed;
  final String? verificationDate;

  ResumeAssessmentItem({
    required this.skillName,
    required this.score,
    required this.level,
    this.passed = true,
    this.verificationDate,
  });

  factory ResumeAssessmentItem.fromJson(Map<String, dynamic> json) {
    return ResumeAssessmentItem(
      skillName: (json['skill_name'] ?? '') as String,
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      level: (json['level'] ?? 'basic') as String,
      passed: json['passed'] as bool? ?? true,
      verificationDate: json['verification_date'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'skill_name': skillName,
      'score': score,
      'level': level,
      'passed': passed,
      'verification_date': verificationDate,
    };
  }
}

class ResumeTailoringMetadata {
  final String? targetRole;
  final String? targetCompany;
  final String? jobId;
  final List<String> matchedSkills;
  final List<String> missingSkills;
  final Map<String, List<String>> evidenceCitations;
  final String? generatedAt;
  final bool antiHallucinationVerified;

  ResumeTailoringMetadata({
    this.targetRole,
    this.targetCompany,
    this.jobId,
    this.matchedSkills = const [],
    this.missingSkills = const [],
    this.evidenceCitations = const {},
    this.generatedAt,
    this.antiHallucinationVerified = true,
  });

  factory ResumeTailoringMetadata.fromJson(Map<String, dynamic> json) {
    final citationsRaw = json['evidence_citations'] as Map<String, dynamic>? ?? {};
    final citations = citationsRaw.map(
      (k, v) => MapEntry(k, (v as List<dynamic>?)?.map((e) => e.toString()).toList() ?? []),
    );

    return ResumeTailoringMetadata(
      targetRole: json['target_role'] as String?,
      targetCompany: json['target_company'] as String?,
      jobId: json['job_id'] as String?,
      matchedSkills: (json['matched_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      missingSkills: (json['missing_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      evidenceCitations: citations,
      generatedAt: json['generated_at'] as String?,
      antiHallucinationVerified: json['anti_hallucination_verified'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'target_role': targetRole,
      'target_company': targetCompany,
      'job_id': jobId,
      'matched_skills': matchedSkills,
      'missing_skills': missingSkills,
      'evidence_citations': evidenceCitations,
      'generated_at': generatedAt,
      'anti_hallucination_verified': antiHallucinationVerified,
    };
  }
}

class ResumeModel {
  final String id;
  final String firebaseUid;
  final String title;
  final String? targetRole;
  final String? jobId;
  final bool isPrimary;
  final ResumeContactInfo contactInfo;
  final String? summary;
  final Map<String, List<ResumeSkillItem>> skillsByCategory;
  final List<ResumeExperienceItem> experience;
  final List<ResumeProjectItem> projects;
  final List<ResumeEducationItem> education;
  final List<ResumeAssessmentItem> practicalAssessments;
  final ResumeTailoringMetadata? tailoringMetadata;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  ResumeModel({
    required this.id,
    required this.firebaseUid,
    required this.title,
    this.targetRole,
    this.jobId,
    this.isPrimary = false,
    required this.contactInfo,
    this.summary,
    this.skillsByCategory = const {},
    this.experience = const [],
    this.projects = const [],
    this.education = const [],
    this.practicalAssessments = const [],
    this.tailoringMetadata,
    this.createdAt,
    this.updatedAt,
  });

  factory ResumeModel.fromJson(Map<String, dynamic> json) {
    final rawSkills = json['skills_by_category'] as Map<String, dynamic>? ?? {};
    final parsedSkills = <String, List<ResumeSkillItem>>{};
    rawSkills.forEach((key, val) {
      if (val is List) {
        parsedSkills[key] = val.map((e) => ResumeSkillItem.fromJson(e as Map<String, dynamic>)).toList();
      }
    });

    return ResumeModel(
      id: (json['id'] ?? '').toString(),
      firebaseUid: (json['firebase_uid'] ?? '') as String,
      title: (json['title'] ?? 'Resume') as String,
      targetRole: json['target_role'] as String?,
      jobId: json['job_id'] as String?,
      isPrimary: json['is_primary'] as bool? ?? false,
      contactInfo: json['contact_info'] != null
          ? ResumeContactInfo.fromJson(json['contact_info'] as Map<String, dynamic>)
          : ResumeContactInfo(name: 'Candidate', email: ''),
      summary: json['summary'] as String?,
      skillsByCategory: parsedSkills,
      experience: (json['experience'] as List<dynamic>?)
              ?.map((e) => ResumeExperienceItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      projects: (json['projects'] as List<dynamic>?)
              ?.map((e) => ResumeProjectItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      education: (json['education'] as List<dynamic>?)
              ?.map((e) => ResumeEducationItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      practicalAssessments: (json['practical_assessments'] as List<dynamic>?)
              ?.map((e) => ResumeAssessmentItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      tailoringMetadata: json['tailoring_metadata'] != null
          ? ResumeTailoringMetadata.fromJson(json['tailoring_metadata'] as Map<String, dynamic>)
          : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    final serializedSkills = <String, dynamic>{};
    skillsByCategory.forEach((k, v) {
      serializedSkills[k] = v.map((e) => e.toJson()).toList();
    });

    return {
      'id': id,
      'firebase_uid': firebaseUid,
      'title': title,
      'target_role': targetRole,
      'job_id': jobId,
      'is_primary': isPrimary,
      'contact_info': contactInfo.toJson(),
      'summary': summary,
      'skills_by_category': serializedSkills,
      'experience': experience.map((e) => e.toJson()).toList(),
      'projects': projects.map((e) => e.toJson()).toList(),
      'education': education.map((e) => e.toJson()).toList(),
      'practical_assessments': practicalAssessments.map((e) => e.toJson()).toList(),
      'tailoring_metadata': tailoringMetadata?.toJson(),
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }
}
