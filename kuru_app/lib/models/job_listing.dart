/// Job & Internship listing model corresponding to FastAPI /api/v1/jobs schemas.
class JobListing {
  final String id;
  final String title;
  final String company;
  final String? location;
  final String? workMode; // remote, hybrid, on-site
  final String? jobType; // full-time, internship, contract
  final String? experienceLevel;
  final String? salaryRange;
  final String sourcePlatform;
  final String sourceUrl;
  final String? description;
  final List<String> requiredSkills;
  final List<String> matchedSkills;
  final List<String> missingSkills;
  final double? matchScore; // 0.0 - 100.0
  final List<String> matchReasons;
  final bool isSaved;
  final DateTime? postedAt;

  JobListing({
    required this.id,
    required this.title,
    required this.company,
    this.location,
    this.workMode,
    this.jobType,
    this.experienceLevel,
    this.salaryRange,
    required this.sourcePlatform,
    required this.sourceUrl,
    this.description,
    this.requiredSkills = const [],
    this.matchedSkills = const [],
    this.missingSkills = const [],
    this.matchScore,
    this.matchReasons = const [],
    this.isSaved = false,
    this.postedAt,
  });

  factory JobListing.fromJson(Map<String, dynamic> json) {
    return JobListing(
      id: (json['id'] ?? json['job_id'] ?? '').toString(),
      title: (json['title'] ?? 'Job Title') as String,
      company: (json['company'] ?? 'Company') as String,
      location: json['location'] as String?,
      workMode: json['work_mode'] as String?,
      jobType: json['job_type'] as String?,
      experienceLevel: json['experience_level'] as String?,
      salaryRange: json['salary_range'] as String?,
      sourcePlatform: (json['source_platform'] ?? json['source'] ?? 'Verified Source') as String,
      sourceUrl: (json['source_url'] ?? json['url'] ?? '') as String,
      description: json['description'] as String?,
      requiredSkills: (json['required_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      matchedSkills: (json['matched_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      missingSkills: (json['missing_skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      matchScore: json['match_score'] != null
          ? (json['match_score'] as num).toDouble()
          : (json['fit_score'] != null ? (json['fit_score'] as num).toDouble() : null),
      matchReasons: (json['match_reasons'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      isSaved: json['is_saved'] as bool? ?? false,
      postedAt: json['posted_at'] != null ? DateTime.tryParse(json['posted_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'company': company,
      'location': location,
      'work_mode': workMode,
      'job_type': jobType,
      'experience_level': experienceLevel,
      'salary_range': salaryRange,
      'source_platform': sourcePlatform,
      'source_url': sourceUrl,
      'description': description,
      'required_skills': requiredSkills,
      'matched_skills': matchedSkills,
      'missing_skills': missingSkills,
      'match_score': matchScore,
      'match_reasons': matchReasons,
      'is_saved': isSaved,
      'posted_at': postedAt?.toIso8601String(),
    };
  }

  JobListing copyWith({bool? isSaved, double? matchScore}) {
    return JobListing(
      id: id,
      title: title,
      company: company,
      location: location,
      workMode: workMode,
      jobType: jobType,
      experienceLevel: experienceLevel,
      salaryRange: salaryRange,
      sourcePlatform: sourcePlatform,
      sourceUrl: sourceUrl,
      description: description,
      requiredSkills: requiredSkills,
      matchedSkills: matchedSkills,
      missingSkills: missingSkills,
      matchScore: matchScore ?? this.matchScore,
      matchReasons: matchReasons,
      isSaved: isSaved ?? this.isSaved,
      postedAt: postedAt,
    );
  }
}
