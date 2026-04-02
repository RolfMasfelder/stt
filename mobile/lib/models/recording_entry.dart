import 'dart:convert';

class RecordingEntry {
  final String id;
  final String filePath;
  final String filename;
  final DateTime createdAt;
  final Duration duration;
  final String? jobId;
  final String status; // 'recorded', 'uploaded', 'completed', 'failed'
  final String? resultSummary;

  const RecordingEntry({
    required this.id,
    required this.filePath,
    required this.filename,
    required this.createdAt,
    required this.duration,
    this.jobId,
    this.status = 'recorded',
    this.resultSummary,
  });

  RecordingEntry copyWith({
    String? jobId,
    String? status,
    String? resultSummary,
  }) {
    return RecordingEntry(
      id: id,
      filePath: filePath,
      filename: filename,
      createdAt: createdAt,
      duration: duration,
      jobId: jobId ?? this.jobId,
      status: status ?? this.status,
      resultSummary: resultSummary ?? this.resultSummary,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'filePath': filePath,
    'filename': filename,
    'createdAt': createdAt.toIso8601String(),
    'durationMs': duration.inMilliseconds,
    'jobId': jobId,
    'status': status,
    'resultSummary': resultSummary,
  };

  factory RecordingEntry.fromJson(Map<String, dynamic> json) {
    return RecordingEntry(
      id: json['id'] as String,
      filePath: json['filePath'] as String,
      filename: json['filename'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      duration: Duration(milliseconds: json['durationMs'] as int? ?? 0),
      jobId: json['jobId'] as String?,
      status: json['status'] as String? ?? 'recorded',
      resultSummary: json['resultSummary'] as String?,
    );
  }

  static String encodeList(List<RecordingEntry> entries) {
    return jsonEncode(entries.map((e) => e.toJson()).toList());
  }

  static List<RecordingEntry> decodeList(String jsonStr) {
    final list = jsonDecode(jsonStr) as List;
    return list
        .map((e) => RecordingEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
