import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/job_application.dart';

/// Service managing job application preparation, human-in-the-loop approval, and lifecycle tracking.
class ApplicationService {
  final ApiClient _client;

  ApplicationService(this._client);

  /// Synthesize application packet (tailored resume + cover note) and queue human approval request.
  Future<ApplicationPrepareResult> prepareApplication({
    required String jobId,
    String? resumeId,
    String? coverNote,
    String? notes,
    String? deadline,
  }) async {
    final payload = <String, dynamic>{
      'job_id': jobId,
      if (resumeId != null && resumeId.isNotEmpty) 'resume_id': resumeId,
      if (coverNote != null && coverNote.isNotEmpty) 'cover_note': coverNote,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
      if (deadline != null && deadline.isNotEmpty) 'deadline': deadline,
    };

    final res = await _client.post(
      '${ApiConfig.applicationsEndpoint}/prepare',
      body: payload,
    );
    return ApplicationPrepareResult.fromJson(res as Map<String, dynamic>);
  }

  /// List tracked applications with optional status filter
  Future<List<JobApplication>> listApplications({String? status}) async {
    final params = <String, dynamic>{
      if (status != null && status.isNotEmpty) 'status': status,
    };

    final res = await _client.get(
      ApiConfig.applicationsEndpoint,
      queryParams: params,
    );

    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    }
    return items.map((e) => JobApplication.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Get single application record by job ID
  Future<JobApplication> getApplication(String jobId) async {
    final res = await _client.get('${ApiConfig.applicationsEndpoint}/$jobId');
    return JobApplication.fromJson(res as Map<String, dynamic>);
  }

  /// Update application status, notes, or deadlines
  Future<JobApplication> updateApplication(
    String jobId, {
    String? status,
    String? notes,
    String? deadline,
    String? submittedAt,
  }) async {
    final payload = <String, dynamic>{
      if (status != null) 'status': status,
      if (notes != null) 'notes': notes,
      if (deadline != null) 'deadline': deadline,
      if (submittedAt != null) 'submitted_at': submittedAt,
    };

    final res = await _client.patch(
      '${ApiConfig.applicationsEndpoint}/$jobId',
      body: payload,
    );
    return JobApplication.fromJson(res as Map<String, dynamic>);
  }

  /// Remove an application tracking record
  Future<void> deleteApplication(String jobId) async {
    await _client.delete('${ApiConfig.applicationsEndpoint}/$jobId');
  }
}
