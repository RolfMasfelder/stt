import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/job_result.dart';
import '../services/server_connection.dart';
import '../services/upload.dart';

class JobEditScreen extends StatefulWidget {
  const JobEditScreen({super.key});

  @override
  State<JobEditScreen> createState() => _JobEditScreenState();
}

class _JobEditScreenState extends State<JobEditScreen> {
  late TextEditingController _textController;
  late TextEditingController _diarizedController;
  late TextEditingController _structuredController;
  late TextEditingController _summaryController;
  JobResult? _job;
  bool _saving = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_job == null) {
      _job = ModalRoute.of(context)!.settings.arguments as JobResult;
      _textController = TextEditingController(text: _job!.resultText ?? '');
      _diarizedController =
          TextEditingController(text: _job!.resultDiarizedText ?? '');
      _structuredController =
          TextEditingController(text: _job!.resultStructuredText ?? '');
      _summaryController =
          TextEditingController(text: _job!.resultSummary ?? '');
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _diarizedController.dispose();
    _structuredController.dispose();
    _summaryController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final upload = context.read<UploadService>();
    final serverUrl = context.read<ServerConnectionService>().config?.serverUrl;

    if (serverUrl == null) return;

    final fields = <String, String>{};
    if (_textController.text != (_job!.resultText ?? '')) {
      fields['result_text'] = _textController.text;
    }
    if (_diarizedController.text != (_job!.resultDiarizedText ?? '')) {
      fields['result_diarized_text'] = _diarizedController.text;
    }
    if (_structuredController.text != (_job!.resultStructuredText ?? '')) {
      fields['result_structured_text'] = _structuredController.text;
    }
    if (_summaryController.text != (_job!.resultSummary ?? '')) {
      fields['result_summary'] = _summaryController.text;
    }

    if (fields.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Keine Änderungen')),
      );
      return;
    }

    setState(() => _saving = true);

    final result = await upload.correctJob(
      serverUrl: serverUrl,
      jobId: _job!.id,
      fields: fields,
    );

    setState(() => _saving = false);

    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Korrektur gespeichert')),
      );
      Navigator.pop(context, result);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Speichern fehlgeschlagen')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Korrektur'),
        actions: [
          if (_saving)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Speichern',
              onPressed: _save,
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildField('Transkript', _textController),
            const SizedBox(height: 16),
            _buildField('Sprecher', _diarizedController),
            const SizedBox(height: 16),
            _buildField('Struktur', _structuredController),
            const SizedBox(height: 16),
            _buildField('Zusammenfassung', _summaryController),
          ],
        ),
      ),
    );
  }

  Widget _buildField(String label, TextEditingController controller) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          maxLines: null,
          minLines: 4,
          decoration: InputDecoration(
            border: const OutlineInputBorder(),
            hintText: '$label eingeben...',
          ),
        ),
      ],
    );
  }
}
