// Stub for non-web platforms. These functions are never called at runtime
// when kIsWeb is false; they exist only to satisfy the conditional import.

Future<Map<String, String>?> authorizeWithPopup({
  required String authorizationEndpoint,
  required String clientId,
  required String redirectUri,
  required List<String> scopes,
}) async =>
    null;

Future<Map<String, dynamic>?> exchangeCodeForTokens({
  required String tokenEndpoint,
  required String clientId,
  required String redirectUri,
  required String code,
  required String codeVerifier,
}) async =>
    null;

Future<Map<String, dynamic>?> refreshTokens({
  required String tokenEndpoint,
  required String clientId,
  required String redirectUri,
  required String refreshToken,
  required List<String> scopes,
}) async =>
    null;
