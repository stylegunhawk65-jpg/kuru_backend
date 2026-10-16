import 'dart:convert';
import 'dart:io';

/// Pure Dart persistent storage for Firebase authentication credentials.
/// Operates cross-platform (Android, Windows, Linux, macOS) without native symlink issues.
class TokenStorage {
  static final TokenStorage _instance = TokenStorage._internal(persistToFile: true);
  factory TokenStorage() => _instance;
  factory TokenStorage.isolated() => TokenStorage._internal(persistToFile: false);

  final bool _persistToFile;
  TokenStorage._internal({bool persistToFile = true}) : _persistToFile = persistToFile;

  String? _cachedToken;
  String? _cachedUid;
  String? _cachedEmail;

  String? get token => _cachedToken;
  String? get uid => _cachedUid;
  String? get email => _cachedEmail;
  bool get hasToken => _cachedToken != null && _cachedToken!.isNotEmpty;

  File? _sessionFile;

  File _getSessionFile() {
    if (_sessionFile != null) return _sessionFile!;
    try {
      final home = Platform.environment['USERPROFILE'] ??
          Platform.environment['HOME'] ??
          Directory.current.path;
      final dir = Directory('$home/.kuru');
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      _sessionFile = File('${dir.path}/session.json');
    } catch (_) {
      _sessionFile = File('kuru_session.json');
    }
    return _sessionFile!;
  }

  /// Initialize session from disk cache
  Future<void> init() async {
    if (!_persistToFile) return;
    try {
      final file = _getSessionFile();
      if (await file.exists()) {
        final content = await file.readAsString();
        if (content.isNotEmpty) {
          final data = jsonDecode(content) as Map<String, dynamic>;
          _cachedToken = data['token'] as String?;
          _cachedUid = data['uid'] as String?;
          _cachedEmail = data['email'] as String?;
        }
      }
    } catch (_) {
      // In-memory fallback if file system access is restricted
    }
  }

  /// Save active credentials
  Future<void> saveCredentials({
    required String token,
    required String uid,
    String? email,
  }) async {
    _cachedToken = token;
    _cachedUid = uid;
    _cachedEmail = email;

    if (!_persistToFile) return;
    try {
      final file = _getSessionFile();
      final data = {
        'token': token,
        'uid': uid,
        'email': email,
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      };
      await file.writeAsString(jsonEncode(data));
    } catch (_) {
      // Retained in memory if file save fails
    }
  }

  /// Clear session credentials on logout or token expiration
  Future<void> clearCredentials() async {
    _cachedToken = null;
    _cachedUid = null;
    _cachedEmail = null;

    if (!_persistToFile) return;
    try {
      final file = _getSessionFile();
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {
      // In-memory state cleared
    }
  }
}
