/// Student Profile data model corresponding to FastAPI /api/v1/profiles schemas.
class StudentProfile {
  final int? id;
  final String firebaseUid;
  final String fullName;
  final String? email;
  final String? headline;
  final String? bio;
  final String? educationLevel;
  final String? fieldOfStudy;
  final String? institutionName;
  final int? graduationYear;
  final List<String> targetRoles;
  final List<String> interests;
  final List<String> preferredLocations;
  final List<String> preferredWorkModes;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  StudentProfile({
    this.id,
    required this.firebaseUid,
    required this.fullName,
    this.email,
    this.headline,
    this.bio,
    this.educationLevel,
    this.fieldOfStudy,
    this.institutionName,
    this.graduationYear,
    this.targetRoles = const [],
    this.interests = const [],
    this.preferredLocations = const [],
    this.preferredWorkModes = const [],
    this.createdAt,
    this.updatedAt,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    return StudentProfile(
      id: json['id'] as int?,
      firebaseUid: (json['firebase_uid'] ?? json['uid'] ?? '') as String,
      fullName: (json['full_name'] ?? 'Student') as String,
      email: json['email'] as String?,
      headline: json['headline'] as String?,
      bio: json['bio'] as String?,
      educationLevel: json['education_level'] as String?,
      fieldOfStudy: json['field_of_study'] as String?,
      institutionName: json['institution_name'] as String?,
      graduationYear: json['graduation_year'] as int?,
      targetRoles: (json['target_roles'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      interests: (json['interests'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      preferredLocations: (json['preferred_locations'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      preferredWorkModes: (json['preferred_work_modes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      'firebase_uid': firebaseUid,
      'full_name': fullName,
      if (email != null) 'email': email,
      if (headline != null) 'headline': headline,
      if (bio != null) 'bio': bio,
      if (educationLevel != null) 'education_level': educationLevel,
      if (fieldOfStudy != null) 'field_of_study': fieldOfStudy,
      if (institutionName != null) 'institution_name': institutionName,
      if (graduationYear != null) 'graduation_year': graduationYear,
      'target_roles': targetRoles,
      'interests': interests,
      'preferred_locations': preferredLocations,
      'preferred_work_modes': preferredWorkModes,
    };
  }

  StudentProfile copyWith({
    String? fullName,
    String? headline,
    String? bio,
    String? educationLevel,
    String? fieldOfStudy,
    String? institutionName,
    int? graduationYear,
    List<String>? targetRoles,
    List<String>? interests,
    List<String>? preferredLocations,
    List<String>? preferredWorkModes,
  }) {
    return StudentProfile(
      id: id,
      firebaseUid: firebaseUid,
      fullName: fullName ?? this.fullName,
      email: email,
      headline: headline ?? this.headline,
      bio: bio ?? this.bio,
      educationLevel: educationLevel ?? this.educationLevel,
      fieldOfStudy: fieldOfStudy ?? this.fieldOfStudy,
      institutionName: institutionName ?? this.institutionName,
      graduationYear: graduationYear ?? this.graduationYear,
      targetRoles: targetRoles ?? this.targetRoles,
      interests: interests ?? this.interests,
      preferredLocations: preferredLocations ?? this.preferredLocations,
      preferredWorkModes: preferredWorkModes ?? this.preferredWorkModes,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
}
