// Web-specific OAuth2 PKCE implementation using dart:html
// ignore: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;
import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

/// Generates a random PKCE code verifier (URL-safe base64, no padding).
String generateCodeVerifier() {
  final random = Random.secure();
  final bytes = Uint8List.fromList(
    List<int>.generate(32, (_) => random.nextInt(256)),
  );
  return base64Url.encode(bytes).replaceAll('=', '');
}

/// Computes the S256 PKCE code challenge from a code verifier.
String computeCodeChallenge(String verifier) {
  final bytes = utf8.encode(verifier);
  final digest = sha256.convert(bytes);
  return base64Url.encode(digest.bytes).replaceAll('=', '');
}

/// Opens a popup window for OAuth2 Authorization Code + PKCE flow.
///
/// Returns a map `{'code': ..., 'verifier': ...}` on success, or null.
Future<Map<String, String>?> authorizeWithPopup({
  required String authorizationEndpoint,
  required String clientId,
  required String redirectUri,
  required List<String> scopes,
}) async {
  final verifier = generateCodeVerifier();
  final challenge = computeCodeChallenge(verifier);
  final state = base64Url
      .encode(
        Uint8List.fromList(
          List<int>.generate(16, (_) => Random.secure().nextInt(256)),
        ),
      )
      .replaceAll('=', '');

  final authUrl = Uri.parse(authorizationEndpoint).replace(
    queryParameters: {
      'response_type': 'code',
      'client_id': clientId,
      'redirect_uri': redirectUri,
      'scope': scopes.join(' '),
      'state': state,
      'code_challenge': challenge,
      'code_challenge_method': 'S256',
    },
  );

  final completer = Completer<Map<String, String>?>();

  final popup = html.window.open(
    authUrl.toString(),
    '_auth_popup',
    'width=600,height=700,left=200,top=100',
  );

  late html.EventListener listener;
  late Timer timeoutTimer;

  listener = (html.Event event) {
    if (event is html.MessageEvent) {
      final data = event.data;
      // callback.html sends a plain string 'oauth_callback:<url>'
      // to avoid JS-object → Dart Map interop issues.
      if (data is String && data.startsWith('oauth_callback:')) {
        final callbackUrl = data.substring('oauth_callback:'.length);
        html.window.removeEventListener('message', listener);
        timeoutTimer.cancel();

        final uri = Uri.parse(callbackUrl);
        final code = uri.queryParameters['code'];
        final returnedState = uri.queryParameters['state'];

        if (code != null && returnedState == state) {
          completer.complete({'code': code, 'verifier': verifier});
        } else {
          completer.complete(null);
        }
      }
    }
  };

  html.window.addEventListener('message', listener);

  timeoutTimer = Timer(const Duration(minutes: 5), () {
    html.window.removeEventListener('message', listener);
    popup.close();
    if (!completer.isCompleted) completer.complete(null);
  });

  return completer.future;
}

/// Exchanges an authorization code for tokens via HTTP POST.
Future<Map<String, dynamic>?> exchangeCodeForTokens({
  required String tokenEndpoint,
  required String clientId,
  required String redirectUri,
  required String code,
  required String codeVerifier,
}) async {
  final response = await http.post(
    Uri.parse(tokenEndpoint),
    body: {
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': redirectUri,
      'client_id': clientId,
      'code_verifier': codeVerifier,
    },
  );
  if (response.statusCode == 200) {
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
  return null;
}

/// Refreshes an access token using the refresh token grant.
Future<Map<String, dynamic>?> refreshTokens({
  required String tokenEndpoint,
  required String clientId,
  required String redirectUri,
  required String refreshToken,
  required List<String> scopes,
}) async {
  final response = await http.post(
    Uri.parse(tokenEndpoint),
    body: {
      'grant_type': 'refresh_token',
      'refresh_token': refreshToken,
      'client_id': clientId,
      'redirect_uri': redirectUri,
      'scope': scopes.join(' '),
    },
  );
  if (response.statusCode == 200) {
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
  return null;
}
