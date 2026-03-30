class ServerConfig {
  final String serverUrl;
  final bool verifyTls;

  const ServerConfig({
    required this.serverUrl,
    this.verifyTls = true,
  });

  ServerConfig copyWith({String? serverUrl, bool? verifyTls}) {
    return ServerConfig(
      serverUrl: serverUrl ?? this.serverUrl,
      verifyTls: verifyTls ?? this.verifyTls,
    );
  }
}
