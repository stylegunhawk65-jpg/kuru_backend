import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:kuru_app/core/api/api_client.dart';
import 'package:kuru_app/core/storage/token_storage.dart';

/// Lightweight in-memory mock client for ApiClient testing
class MockHttpClient extends http.BaseClient {
  http.Response Function(http.BaseRequest request)? handler;

  MockHttpClient([this.handler]);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final response = handler != null
        ? handler!(request)
        : http.Response('{"status": "ok"}', 200, headers: {'content-type': 'application/json'});

    return http.StreamedResponse(
      Stream.fromIterable([utf8.encode(response.body)]),
      response.statusCode,
      headers: response.headers,
    );
  }
}

void main() {
  group('ApiClient Tests', () {
    late TokenStorage storage;

    setUp(() async {
      storage = TokenStorage();
      await storage.clearCredentials();
    });

    test('injects Bearer token in headers when token is stored', () async {
      await storage.saveCredentials(
        token: 'firebase_token_secret_xyz',
        uid: 'user_123',
      );

      http.BaseRequest? capturedRequest;
      final mock = MockHttpClient((req) {
        capturedRequest = req;
        return http.Response('{"result": "success"}', 200, headers: {'content-type': 'application/json'});
      });

      final client = ApiClient(client: mock, storage: storage);
      final res = await client.get('http://127.0.0.1:8000/api/v1/profiles/me');

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.headers['Authorization'], 'Bearer firebase_token_secret_xyz');
      expect(capturedRequest!.headers['Accept'], 'application/json');
      expect(res['result'], 'success');
    });

    test('triggers onAuthExpired and throws AuthExpiredException on 401', () async {
      bool expiredCallbackCalled = false;

      final mock = MockHttpClient((req) {
        return http.Response(
          '{"detail": "Firebase ID token has expired. Please refresh your credentials."}',
          401,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = ApiClient(
        client: mock,
        storage: storage,
        onAuthExpired: () {
          expiredCallbackCalled = true;
        },
      );

      await expectLater(
        () => client.get('http://127.0.0.1:8000/api/v1/profiles/me'),
        throwsA(isA<AuthExpiredException>()),
      );

      expect(expiredCallbackCalled, isTrue);
    });

    test('handles 404 and 500 error responses by throwing ApiException', () async {
      final mock = MockHttpClient((req) {
        return http.Response(
          '{"detail": "Profile not found"}',
          404,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = ApiClient(client: mock, storage: storage);

      try {
        await client.get('http://127.0.0.1:8000/api/v1/profiles/me');
        fail('Should have thrown ApiException');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
        expect(e.message, contains('Profile not found'));
      }
    });

    test('sends JSON body in POST requests', () async {
      http.BaseRequest? capturedRequest;
      final mock = MockHttpClient((req) {
        capturedRequest = req;
        return http.Response('{"id": 1, "status": "created"}', 201, headers: {'content-type': 'application/json'});
      });

      final client = ApiClient(client: mock, storage: storage);
      final res = await client.post(
        'http://127.0.0.1:8000/api/v1/profiles',
        body: {'full_name': 'Test Student', 'target_roles': ['Backend Engineer']},
      );

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.headers['Content-Type'], 'application/json');
      expect(res['status'], 'created');
    });
  });
}
