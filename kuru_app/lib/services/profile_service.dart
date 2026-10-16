import '../core/api/api_client.dart';
import '../core/config/api_config.dart';
import '../models/user_profile.dart';

/// Service managing Career Profile operations against /api/v1/profiles
class ProfileService {
  final ApiClient _client;

  ProfileService(this._client);

  /// Fetch current user's career profile
  Future<StudentProfile?> getMyProfile() async {
    try {
      final data = await _client.get(ApiConfig.myProfileEndpoint);
      if (data != null && data is Map<String, dynamic>) {
        return StudentProfile.fromJson(data);
      }
      return null;
    } on ApiException catch (e) {
      if (e.statusCode == 404) {
        return null; // Profile not created yet
      }
      rethrow;
    }
  }

  /// Create a new career profile
  Future<StudentProfile> createProfile(StudentProfile profile) async {
    final payload = profile.toJson();
    final data = await _client.post(ApiConfig.profilesEndpoint, body: payload);
    return StudentProfile.fromJson(data as Map<String, dynamic>);
  }

  /// Update an existing career profile
  Future<StudentProfile> updateProfile(StudentProfile profile) async {
    final payload = profile.toJson();
    final data = await _client.put(ApiConfig.profilesEndpoint, body: payload);
    return StudentProfile.fromJson(data as Map<String, dynamic>);
  }
}
