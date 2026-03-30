class ResultVersion {
  final String id;
  final int version;
  final String? resultText;
  final String? resultDiarizedText;
  final String? resultStructuredText;
  final String? resultSummary;
  final String source;
  final DateTime createdAt;

  const ResultVersion({
    required this.id,
    required this.version,
    this.resultText,
    this.resultDiarizedText,
    this.resultStructuredText,
    this.resultSummary,
    required this.source,
    required this.createdAt,
  });

  factory ResultVersion.fromJson(Map<String, dynamic> json) {
    return ResultVersion(
      id: json['id'] as String,
      version: json['version'] as int,
      resultText: json['result_text'] as String?,
      resultDiarizedText: json['result_diarized_text'] as String?,
      resultStructuredText: json['result_structured_text'] as String?,
      resultSummary: json['result_summary'] as String?,
      source: json['source'] as String? ?? 'pipeline',
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  static List<ResultVersion> fromJsonList(List<dynamic> jsonList) {
    return jsonList
        .map((e) => ResultVersion.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
