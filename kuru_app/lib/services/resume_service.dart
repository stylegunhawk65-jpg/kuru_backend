import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/resume.dart';

/// Service managing ATS resume generation, customization, regeneration, and PDF export.
class ResumeService {
  final ApiClient _client;

  ResumeService(this._client);

  /// Generate tailored, evidence-backed ATS resume from profile, GitHub repos, and practical assessments.
  Future<ResumeModel> generateResume({
    String? targetRole,
    String? jobId,
    bool saveToDb = true,
  }) async {
    final payload = <String, dynamic>{
      if (targetRole != null && targetRole.isNotEmpty) 'target_role': targetRole,
      if (jobId != null && jobId.isNotEmpty) 'job_id': jobId,
      'save_to_db': saveToDb,
    };

    final res = await _client.post(
      '${ApiConfig.resumesEndpoint}/generate',
      body: payload,
    );
    return ResumeModel.fromJson(res as Map<String, dynamic>);
  }

  /// List saved resumes for current authenticated user
  Future<List<ResumeModel>> listResumes({String? targetRole}) async {
    final params = <String, dynamic>{
      if (targetRole != null && targetRole.isNotEmpty) 'target_role': targetRole,
    };

    final res = await _client.get(
      ApiConfig.resumesEndpoint,
      queryParams: params,
    );

    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    }
    return items.map((e) => ResumeModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Get single resume by ID
  Future<ResumeModel> getResume(String id) async {
    final res = await _client.get('${ApiConfig.resumesEndpoint}/$id');
    return ResumeModel.fromJson(res as Map<String, dynamic>);
  }

  /// Save new custom resume
  Future<ResumeModel> createResume(Map<String, dynamic> data) async {
    final res = await _client.post(
      ApiConfig.resumesEndpoint,
      body: data,
    );
    return ResumeModel.fromJson(res as Map<String, dynamic>);
  }

  /// Update an existing resume
  Future<ResumeModel> updateResume(String id, Map<String, dynamic> updates) async {
    final res = await _client.put(
      '${ApiConfig.resumesEndpoint}/$id',
      body: updates,
    );
    return ResumeModel.fromJson(res as Map<String, dynamic>);
  }

  /// Re-synthesize resume against updated skills, assessments, or job description
  Future<ResumeModel> regenerateResume(
    String id, {
    String? targetRole,
    String? jobId,
  }) async {
    final payload = <String, dynamic>{
      if (targetRole != null && targetRole.isNotEmpty) 'target_role': targetRole,
      if (jobId != null && jobId.isNotEmpty) 'job_id': jobId,
      'save_to_db': true,
    };

    final res = await _client.post(
      '${ApiConfig.resumesEndpoint}/$id/regenerate',
      body: payload,
    );
    return ResumeModel.fromJson(res as Map<String, dynamic>);
  }

  /// Delete a resume document
  Future<void> deleteResume(String id) async {
    await _client.delete('${ApiConfig.resumesEndpoint}/$id');
  }

  /// Download ATS formatted PDF binary stream
  Future<List<int>> downloadResumePdf(String id) async {
    return await _client.getBytes('${ApiConfig.resumesEndpoint}/$id/pdf');
  }
}
