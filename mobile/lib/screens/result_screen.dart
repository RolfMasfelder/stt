import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../models/upload_status.dart';
import '../services/upload.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final upload = context.watch<UploadService>();
    final job = upload.currentJob;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ergebnis'),
        actions: [
          if (job != null && job.isCompleted)
            IconButton(
              icon: const Icon(Icons.copy),
              tooltip: 'Alles kopieren',
              onPressed: () => _copyAll(context, upload),
            ),
        ],
      ),
      body: _buildBody(context, upload),
    );
  }

  Widget _buildBody(BuildContext context, UploadService upload) {
    switch (upload.status) {
      case UploadStatus.idle:
        return const Center(child: Text('Kein aktiver Auftrag'));

      case UploadStatus.uploading:
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(value: upload.progress),
              const SizedBox(height: 16),
              const Text('Wird hochgeladen...'),
            ],
          ),
        );

      case UploadStatus.processing:
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text('Verarbeitung läuft... (${upload.currentJob?.status})'),
            ],
          ),
        );

      case UploadStatus.failed:
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text(
                upload.errorMessage ?? 'Unbekannter Fehler',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () {
                  upload.reset();
                  Navigator.pop(context);
                },
                child: const Text('Zurück'),
              ),
            ],
          ),
        );

      case UploadStatus.completed:
        return _buildResults(context, upload);
    }
  }

  Widget _buildResults(BuildContext context, UploadService upload) {
    final job = upload.currentJob;
    if (job == null) return const SizedBox.shrink();

    return DefaultTabController(
      length: _tabCount(job.resultText, job.resultDiarizedText,
          job.resultStructuredText, job.resultSummary),
      child: Column(
        children: [
          TabBar(
            isScrollable: true,
            tabs: [
              if (job.resultSummary != null)
                const Tab(text: 'Zusammenfassung'),
              if (job.resultStructuredText != null)
                const Tab(text: 'Struktur'),
              if (job.resultDiarizedText != null)
                const Tab(text: 'Sprecher'),
              if (job.resultText != null) const Tab(text: 'Transkript'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                if (job.resultSummary != null)
                  _resultTab(context, job.resultSummary!),
                if (job.resultStructuredText != null)
                  _resultTab(context, job.resultStructuredText!),
                if (job.resultDiarizedText != null)
                  _resultTab(context, job.resultDiarizedText!),
                if (job.resultText != null)
                  _resultTab(context, job.resultText!),
              ],
            ),
          ),
        ],
      ),
    );
  }

  int _tabCount(String? text, String? diarized, String? structured,
      String? summary) {
    int count = 0;
    if (summary != null) count++;
    if (structured != null) count++;
    if (diarized != null) count++;
    if (text != null) count++;
    return count;
  }

  Widget _resultTab(BuildContext context, String content) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: content));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Kopiert')),
                  );
                },
                icon: const Icon(Icons.copy, size: 16),
                label: const Text('Kopieren'),
              ),
            ],
          ),
          SelectableText(
            content,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }

  void _copyAll(BuildContext context, UploadService upload) {
    final job = upload.currentJob;
    if (job == null) return;

    final buffer = StringBuffer();
    if (job.resultSummary != null) {
      buffer.writeln('## Zusammenfassung\n');
      buffer.writeln(job.resultSummary);
      buffer.writeln();
    }
    if (job.resultStructuredText != null) {
      buffer.writeln('## Struktur\n');
      buffer.writeln(job.resultStructuredText);
      buffer.writeln();
    }
    if (job.resultDiarizedText != null) {
      buffer.writeln('## Sprecher\n');
      buffer.writeln(job.resultDiarizedText);
      buffer.writeln();
    }
    if (job.resultText != null) {
      buffer.writeln('## Transkript\n');
      buffer.writeln(job.resultText);
    }

    Clipboard.setData(ClipboardData(text: buffer.toString()));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Alle Ergebnisse kopiert')),
    );
  }
}
