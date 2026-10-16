import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../storage/token_storage.dart';

/// Exception thrown when the backend returns 401 Unauthorized or expired token.
class AuthExpiredException implements Exception {
  final String message;
  const AuthExpiredException([this.message = 'Authentication required or token expired.']);

  @override
  String toString() => 'AuthExpiredException: $message';
}

/// Exception thrown when the backend returns a non-2xx status code.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  final dynamic details;

  const ApiException({
    required this.statusCode,
    required this.message,
    this.details,
  });

  @override
  String toString() => 'ApiException [$statusCode]: $message';
}

/// Exception thrown on socket, timeout, or DNS connectivity failures.
class NetworkException implements Exception {
  final String message;
  const NetworkException(this.message);

  @override
  String toString() => 'NetworkException: $message';
}

/// Centralized HTTP client managing authentication headers, response decoding, and error interceptors.
class ApiClient {
  final http.Client _client;
  final TokenStorage _storage;

  // Callback notified when an authenticated request receives a 401
  void Function()? onAuthExpired;

  // Optional dynamic token provider (e.g. Firebase Auth getIdToken)
  Future<String?> Function()? tokenProvider;

  ApiClient({
    http.Client? client,
    TokenStorage? storage,
    this.tokenProvider,
    this.onAuthExpired,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? TokenStorage();

  /// Ensure token is refreshed if dynamic provider is configured
  Future<void> _ensureFreshToken() async {
    if (tokenProvider != null) {
      try {
        final freshToken = await tokenProvider!();
        if (freshToken != null && freshToken.isNotEmpty && freshToken != _storage.token) {
          await _storage.saveCredentials(
            token: freshToken,
            uid: _storage.uid ?? '',
            email: _storage.email,
          );
        }
      } catch (_) {}
    }
  }

  /// Build standard headers with Bearer token injection
  Map<String, String> _buildHeaders({Map<String, String>? extraHeaders}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    final token = _storage.token;
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    if (extraHeaders != null) {
      headers.addAll(extraHeaders);
    }
    return headers;
  }

  /// Process HTTP response and handle error statuses
  dynamic _processResponse(http.Response response) {
    final statusCode = response.statusCode;

    // Handle 401 Unauthorized explicitly
    if (statusCode == 401) {
      String detail = 'Authentication required or token expired.';
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map && decoded.containsKey('detail')) {
          detail = decoded['detail'].toString();
        }
      } catch (_) {}

      onAuthExpired?.call();
      throw AuthExpiredException(detail);
    }

    // Success responses (200 - 299)
    if (statusCode >= 200 && statusCode < 300) {
      if (response.body.isEmpty) return null;
      try {
        return jsonDecode(response.body);
      } catch (_) {
        return response.body;
      }
    }

    // Client/Server errors (4xx, 5xx)
    String errorMsg = 'HTTP $statusCode Error';
    dynamic errorDetails;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map) {
        if (decoded.containsKey('detail')) {
          final detail = decoded['detail'];
          errorMsg = detail is String ? detail : jsonEncode(detail);
        } else if (decoded.containsKey('message')) {
          errorMsg = decoded['message'].toString();
        }
        errorDetails = decoded;
      }
    } catch (_) {
      errorMsg = response.body.isNotEmpty ? response.body : 'Request failed with status $statusCode';
    }

    throw ApiException(
      statusCode: statusCode,
      message: errorMsg,
      details: errorDetails,
    );
  }

  /// Execute GET request
  Future<dynamic> get(
    String url, {
    Map<String, dynamic>? queryParams,
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      Uri uri = Uri.parse(url);
      if (queryParams != null && queryParams.isNotEmpty) {
        final params = queryParams.map((k, v) => MapEntry(k, v?.toString() ?? ''));
        uri = uri.replace(queryParameters: {...uri.queryParameters, ...params});
      }

      final response = await _client
          .get(uri, headers: _buildHeaders(extraHeaders: headers))
          .timeout(ApiConfig.requestTimeout);
      return _processResponse(response);
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }

  /// Execute POST request
  Future<dynamic> post(
    String url, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      final uri = Uri.parse(url);
      final payload = body != null ? jsonEncode(body) : null;
      final response = await _client
          .post(uri, headers: _buildHeaders(extraHeaders: headers), body: payload)
          .timeout(ApiConfig.requestTimeout);
      return _processResponse(response);
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }

  /// Execute PUT request
  Future<dynamic> put(
    String url, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      final uri = Uri.parse(url);
      final payload = body != null ? jsonEncode(body) : null;
      final response = await _client
          .put(uri, headers: _buildHeaders(extraHeaders: headers), body: payload)
          .timeout(ApiConfig.requestTimeout);
      return _processResponse(response);
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }

  /// Execute DELETE request
  Future<dynamic> delete(
    String url, {
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      final uri = Uri.parse(url);
      final response = await _client
          .delete(uri, headers: _buildHeaders(extraHeaders: headers))
          .timeout(ApiConfig.requestTimeout);
      return _processResponse(response);
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }

  /// Execute PATCH request
  Future<dynamic> patch(
    String url, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      final uri = Uri.parse(url);
      final payload = body != null ? jsonEncode(body) : null;
      final response = await _client
          .patch(uri, headers: _buildHeaders(extraHeaders: headers), body: payload)
          .timeout(ApiConfig.requestTimeout);
      return _processResponse(response);
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }

  /// Execute GET request returning binary bytes (e.g. for PDF downloads)
  Future<List<int>> getBytes(
    String url, {
    Map<String, dynamic>? queryParams,
    Map<String, String>? headers,
  }) async {
    try {
      await _ensureFreshToken();
      Uri uri = Uri.parse(url);
      if (queryParams != null && queryParams.isNotEmpty) {
        final params = queryParams.map((k, v) => MapEntry(k, v?.toString() ?? ''));
        uri = uri.replace(queryParameters: {...uri.queryParameters, ...params});
      }

      final requestHeaders = _buildHeaders(extraHeaders: headers);
      requestHeaders['Accept'] = 'application/pdf, application/octet-stream, */*';

      final response = await _client
          .get(uri, headers: requestHeaders)
          .timeout(ApiConfig.requestTimeout);

      if (response.statusCode == 401) {
        onAuthExpired?.call();
        throw const AuthExpiredException();
      }
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response.bodyBytes;
      }
      throw ApiException(
        statusCode: response.statusCode,
        message: 'Failed to download binary file: HTTP ${response.statusCode}',
      );
    } on SocketException catch (e) {
      throw NetworkException('Could not connect to backend server at $url: ${e.message}');
    } on TimeoutException {
      throw const NetworkException('Request timed out. Please check your network connection.');
    } on AuthExpiredException {
      rethrow;
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException('Network error: $e');
    }
  }
}

