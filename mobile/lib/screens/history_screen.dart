import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/recording_entry.dart';
import '../services/recording_history.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final history = context.watch<RecordingHistoryService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Aufnahmen'),
      ),
      body: history.entries.isEmpty
          ? const Center(
              child: Text(
                'Noch keine Aufnahmen',
                style: TextStyle(color: Colors.grey),
              ),
            )
          : ListView.builder(
              itemCount: history.entries.length,
              itemBuilder: (context, index) {
                final entry = history.entries[index];
                return _EntryTile(entry: entry);
              },
            ),
    );
  }
}

class _EntryTile extends StatelessWidget {
  final RecordingEntry entry;

  const _EntryTile({required this.entry});

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('dd.MM.yyyy HH:mm');
    final duration = _formatDuration(entry.duration);

    return ListTile(
      leading: Icon(
        _statusIcon(entry.status),
        color: _statusColor(entry.status),
      ),
      title: Text(entry.filename),
      subtitle: Text(
        '${dateFormat.format(entry.createdAt.toLocal())} · $duration',
      ),
      trailing: _buildTrailing(context),
      onTap: entry.status == 'completed'
          ? () => _showResult(context)
          : null,
    );
  }

  Widget? _buildTrailing(BuildContext context) {
    switch (entry.status) {
      case 'uploaded':
      case 'processing':
        return const SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        );
      case 'completed':
        return const Icon(Icons.chevron_right);
      case 'failed':
        return const Icon(Icons.error_outline, color: Colors.red);
      default:
        return PopupMenuButton<String>(
          onSelected: (value) {
            if (value == 'delete') {
              context.read<RecordingHistoryService>().remove(entry.id);
            }
          },
          itemBuilder: (_) => [
            const PopupMenuItem(
              value: 'delete',
              child: Text('Löschen'),
            ),
          ],
        );
    }
  }

  void _showResult(BuildContext context) {
    if (entry.resultSummary != null) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(entry.filename),
          content: SingleChildScrollView(
            child: SelectableText(entry.resultSummary!),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Schließen'),
            ),
          ],
        ),
      );
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'recorded':
        return Icons.mic;
      case 'uploaded':
      case 'processing':
        return Icons.cloud_upload;
      case 'completed':
        return Icons.check_circle;
      case 'failed':
        return Icons.error;
      default:
        return Icons.circle;
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'recorded':
        return Colors.grey;
      case 'uploaded':
      case 'processing':
        return Colors.orange;
      case 'completed':
        return Colors.green;
      case 'failed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }
}
