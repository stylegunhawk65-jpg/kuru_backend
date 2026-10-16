import 'job_listing.dart';

/// Application tracking model representing job applications with lifecycle states.
class JobApplication {
  final String id;
  final String firebaseUid;
  final String jobId;
  final String status; // saved, applied, interviewing, offered, rejected, archived
  final String? notes;
  final String? deadline;
  final String? submittedAt;
  final String? resumeId;
  final Map<String, dynamic> applicationPacket;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final JobListing? job;

  JobApplication({
    required this.id,
    required this.firebaseUid,
    required this.jobId,
    required this.status,
    this.notes,
    this.deadline,
    this.submittedAt,
    this.resumeId,
    this.applicationPacket = const {},
    this.createdAt,
    this.updatedAt,
    this.job,
  });

  factory JobApplication.fromJson(Map<String, dynamic> json) {
    return JobApplication(
      id: (json['id'] ?? '').toString(),
      firebaseUid: (json['firebase_uid'] ?? '') as String,
      jobId: (json['job_id'] ?? '') as String,
      status: (json['status'] ?? 'saved') as String,
      notes: json['notes'] as String?,
      deadline: json['deadline'] as String?,
      submittedAt: json['submitted_at'] as String?,
      resumeId: json['resume_id'] as String?,
      applicationPacket: (json['application_packet'] as Map<String, dynamic>?) ?? {},
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at'].toString()) : null,
      job: json['job'] != null ? JobListing.fromJson(json['job'] as Map<String, dynamic>) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'firebase_uid': firebaseUid,
      'job_id': jobId,
      'status': status,
      'notes': notes,
      'deadline': deadline,
      'submitted_at': submittedAt,
      'resume_id': resumeId,
      'application_packet': applicationPacket,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'job': job?.toJson(),
    };
  }

  JobApplication copyWith({
    String? status,
    String? notes,
    String? deadline,
    String? submittedAt,
  }) {
    return JobApplication(
      id: id,
      firebaseUid: firebaseUid,
      jobId: jobId,
      status: status ?? this.status,
      notes: notes ?? this.notes,
      deadline: deadline ?? this.deadline,
      submittedAt: submittedAt ?? this.submittedAt,
      resumeId: resumeId,
      applicationPacket: applicationPacket,
      createdAt: createdAt,
      updatedAt: updatedAt,
      job: job,
    );
  }
}

/// Result returned when preparing an application and queuing human approval gate.
class ApplicationPrepareResult {
  final String jobId;
  final int approvalRequestId;
  final String status;
  final Map<String, dynamic> applicationPacket;

  ApplicationPrepareResult({
    required this.jobId,
    required this.approvalRequestId,
    required this.status,
    required this.applicationPacket,
  });

  factory ApplicationPrepareResult.fromJson(Map<String, dynamic> json) {
    return ApplicationPrepareResult(
      jobId: (json['job_id'] ?? '').toString(),
      approvalRequestId: (json['approval_request_id'] as num?)?.toInt() ?? 0,
      status: (json['status'] ?? 'pending_approval') as String,
      applicationPacket: (json['application_packet'] as Map<String, dynamic>?) ?? {},
    );
  }
}
