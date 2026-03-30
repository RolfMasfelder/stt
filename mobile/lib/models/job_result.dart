class JobResult {
  final String id;
  final String status;
  final String originalFilename;
  final String whisperModel;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final String? resultText;
  final String? resultDiarizedText;
  final String? resultStructuredText;
  final String? resultSummary;
  final String? errorMessage;

  const JobResult({
    required this.id,
    required this.status,
    required this.originalFilename,
    required this.whisperModel,
    required this.createdAt,
    this.updatedAt,
    this.resultText,
    this.resultDiarizedText,
    this.resultStructuredText,
    this.resultSummary,
    this.errorMessage,
  });

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending' || status == 'running';

  factory JobResult.fromJson(Map<String, dynamic> json) {
    return JobResult(
      id: json['id'] as String,
      status: json['status'] as String,
      originalFilename: json['original_filename'] as String? ?? '',
      whisperModel: json['whisper_model'] as String? ?? 'small',
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
      resultText: json['result_text'] as String?,
      resultDiarizedText: json['result_diarized_text'] as String?,
      resultStructuredText: json['result_structured_text'] as String?,
      resultSummary: json['result_summary'] as String?,
      errorMessage: json['error_message'] as String?,
    );
  }
}
