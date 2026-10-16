import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/job_listing.dart';

/// Service managing Job and Internship discovery, match ranking, and saved jobs.
class JobsService {
  final ApiClient _client;

  JobsService(this._client);

  /// Search and filter jobs with transparent match breakdown
  Future<List<JobListing>> searchJobs({
    String? query,
    String? role,
    String? workMode,
    String? jobType,
    int page = 1,
    int pageSize = 10,
  }) async {
    final params = <String, dynamic>{
      if (query != null && query.isNotEmpty) 'q': query,
      if (role != null && role.isNotEmpty) 'role': role,
      if (workMode != null && workMode.isNotEmpty) 'work_mode': workMode,
      if (jobType != null && jobType.isNotEmpty) 'job_type': jobType,
      'page': page,
      'page_size': pageSize,
    };

    final res = await _client.get(ApiConfig.jobsEndpoint, queryParams: params);
    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    } else if (res is Map && res.containsKey('jobs')) {
      items = res['jobs'] as List<dynamic>;
    }

    return items.map((e) => JobListing.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Get specific job details
  Future<JobListing> getJobDetails(String jobId) async {
    final res = await _client.get('${ApiConfig.jobsEndpoint}/$jobId');
    return JobListing.fromJson(res as Map<String, dynamic>);
  }

  /// Bookmark/save a job
  Future<void> saveJob(String jobId) async {
    await _client.post('${ApiConfig.jobsEndpoint}/$jobId/save');
  }

  /// Unsave a previously bookmarked job
  Future<void> unsaveJob(String jobId) async {
    await _client.delete('${ApiConfig.jobsEndpoint}/$jobId/save');
  }

  /// Fetch user's saved jobs
  Future<List<JobListing>> getSavedJobs() async {
    final res = await _client.get(ApiConfig.savedJobsEndpoint);
    List<dynamic> items = [];
    if (res is List) {
      items = res;
    } else if (res is Map && res.containsKey('items')) {
      items = res['items'] as List<dynamic>;
    }
    return items.map((e) => JobListing.fromJson(e as Map<String, dynamic>)).toList();
  }
}
