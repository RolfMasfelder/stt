import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/job_result.dart';
import '../models/result_version.dart';
import '../services/server_connection.dart';
import '../services/upload.dart';

/// Arguments passed when navigating to this screen.
class JobDetailArgs {
  final String jobId;
  const JobDetailArgs({required this.jobId});
}

class JobDetailScreen extends StatefulWidget {
  const JobDetailScreen({super.key});

  @override
  State<JobDetailScreen> createState() => _JobDetailScreenState();
}

class _JobDetailScreenState extends State<JobDetailScreen> {
  JobResult? _job;
  List<ResultVersion> _versions = [];
  bool _loading = true;
  bool _reprocessing = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loading && _job == null) {
      _loadJob();
    }
  }

  Future<void> _loadJob() async {
    final args = ModalRoute.of(context)!.settings.arguments as JobDetailArgs;
    final upload = context.read<UploadService>();
    final serverUrl = context.read<ServerConnectionService>().config?.serverUrl;

    if (serverUrl == null) {
      setState(() {
        _error = 'Kein Server konfiguriert';
        _loading = false;
      });
      return;
    }

    final job = await upload.fetchJob(serverUrl: serverUrl, jobId: args.jobId);

    if (job == null) {
      setState(() {
        _error = 'Job nicht gefunden';
        _loading = false;
      });
      return;
    }

    final versions = await upload.fetchVersions(
      serverUrl: serverUrl,
      jobId: args.jobId,
    );

    setState(() {
      _job = job;
      _versions = versions;
      _loading = false;
    });
  }

  Future<void> _onReprocess(List<String> steps) async {
    final upload = context.read<UploadService>();
    final serverUrl = context.read<ServerConnectionService>().config!.serverUrl;

    setState(() => _reprocessing = true);

    final result = await upload.reprocessJob(
      serverUrl: serverUrl,
      jobId: _job!.id,
      steps: steps,
    );

    if (result != null) {
      final versions = await upload.fetchVersions(
        serverUrl: serverUrl,
        jobId: _job!.id,
      );
      setState(() {
        _job = result;
        _versions = versions;
        _reprocessing = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Neu verarbeitet')));
      }
    } else {
      setState(() => _reprocessing = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Verarbeitung fehlgeschlagen')),
        );
      }
    }
  }

  void _onEdit() {
    Navigator.pushNamed(context, '/job/edit', arguments: _job).then((result) {
      if (result is JobResult) {
        _loadJob(); // Reload to get updated versions too
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Job-Details'),
        actions: [
          if (_job != null && _job!.isCompleted) ...[
            IconButton(
              icon: const Icon(Icons.edit),
              tooltip: 'Korrigieren',
              onPressed: _onEdit,
            ),
            PopupMenuButton<List<String>>(
              icon: const Icon(Icons.replay),
              tooltip: 'Neu verarbeiten',
              enabled: !_reprocessing,
              onSelected: _onReprocess,
              itemBuilder: (_) => [
                const PopupMenuItem(
                  value: ['structure'],
                  child: Text('Struktur neu erstellen'),
                ),
                const PopupMenuItem(
                  value: ['summarize'],
                  child: Text('Zusammenfassung neu erstellen'),
                ),
                const PopupMenuItem(
                  value: ['structure', 'summarize'],
                  child: Text('Beides neu erstellen'),
                ),
              ],
            ),
          ],
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Text(_error!, style: const TextStyle(color: Colors.red)),
      );
    }

    if (_reprocessing) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Wird neu verarbeitet...'),
          ],
        ),
      );
    }

    final job = _job!;

    return DefaultTabController(
      length: _resultTabCount(job) + 1, // +1 for versions tab
      child: Column(
        children: [
          TabBar(
            isScrollable: true,
            tabs: [
              if (_hasContent(job.resultSummary))
                const Tab(text: 'Zusammenfassung'),
              if (_hasContent(job.resultStructuredText))
                const Tab(text: 'Struktur'),
              if (_hasContent(job.resultDiarizedText))
                const Tab(text: 'Sprecher'),
              if (_hasContent(job.resultText)) const Tab(text: 'Transkript'),
              const Tab(text: 'Versionen'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                if (_hasContent(job.resultSummary))
                  _resultTab(job.resultSummary!),
                if (_hasContent(job.resultStructuredText))
                  _resultTab(job.resultStructuredText!),
                if (_hasContent(job.resultDiarizedText))
                  _resultTab(job.resultDiarizedText!),
                if (_hasContent(job.resultText)) _resultTab(job.resultText!),
                _versionsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  bool _hasContent(String? value) => value != null && value.isNotEmpty;

  int _resultTabCount(JobResult job) {
    int count = 0;
    if (_hasContent(job.resultSummary)) count++;
    if (_hasContent(job.resultStructuredText)) count++;
    if (_hasContent(job.resultDiarizedText)) count++;
    if (_hasContent(job.resultText)) count++;
    return count;
  }

  Widget _resultTab(String content) {
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
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(const SnackBar(content: Text('Kopiert')));
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

  Widget _versionsTab() {
    if (_versions.isEmpty) {
      return const Center(
        child: Text(
          'Keine Versionen vorhanden',
          style: TextStyle(color: Colors.grey),
        ),
      );
    }

    final dateFormat = DateFormat('dd.MM.yyyy HH:mm');

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _versions.length,
      itemBuilder: (context, index) {
        final v = _versions[index];
        return Card(
          child: ListTile(
            leading: CircleAvatar(child: Text('v${v.version}')),
            title: Text(_sourceLabel(v.source)),
            subtitle: Text(dateFormat.format(v.createdAt.toLocal())),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _showVersionDetail(v),
          ),
        );
      },
    );
  }

  String _sourceLabel(String source) {
    switch (source) {
      case 'pipeline':
        return 'Original (Pipeline)';
      case 'correction':
        return 'Korrektur';
      case 'reprocess':
        return 'Neu verarbeitet';
      default:
        return source;
    }
  }

  void _showVersionDetail(ResultVersion v) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.95,
        expand: false,
        builder: (_, controller) => Padding(
          padding: const EdgeInsets.all(16),
          child: ListView(
            controller: controller,
            children: [
              Text(
                'Version ${v.version} — ${_sourceLabel(v.source)}',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              if (_hasContent(v.resultSummary)) ...[
                Text(
                  'Zusammenfassung',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 4),
                SelectableText(v.resultSummary!),
                const Divider(height: 24),
              ],
              if (_hasContent(v.resultStructuredText)) ...[
                Text('Struktur', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                SelectableText(v.resultStructuredText!),
                const Divider(height: 24),
              ],
              if (_hasContent(v.resultText)) ...[
                Text(
                  'Transkript',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 4),
                SelectableText(v.resultText!),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
