import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/server_config.dart';
import '../models/connection_status.dart';
import '../services/server_connection.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;
  bool _verifyTls = true;
  bool _testing = false;

  @override
  void initState() {
    super.initState();
    final connection =
        Provider.of<ServerConnectionService>(context, listen: false);
    _urlController =
        TextEditingController(text: connection.config?.serverUrl ?? '');
    _verifyTls = connection.config?.verifyTls ?? true;
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _saveAndTest() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    // Basic URL validation
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ungültige Server-URL')),
      );
      return;
    }

    setState(() => _testing = true);

    final connection =
        Provider.of<ServerConnectionService>(context, listen: false);
    await connection.updateConfig(
      ServerConfig(serverUrl: url, verifyTls: _verifyTls),
    );
    await connection.testConnection();

    if (!mounted) return;
    setState(() => _testing = false);

    final status = connection.status;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          status == ConnectionStatus.connected
              ? 'Verbindung erfolgreich'
              : 'Verbindung fehlgeschlagen',
        ),
        backgroundColor: status == ConnectionStatus.connected
            ? Colors.green.shade800
            : Colors.red.shade800,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Einstellungen'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Server-Verbindung',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'Server-URL',
              hintText: 'https://stt.example.com',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.dns),
            ),
            keyboardType: TextInputType.url,
            autocorrect: false,
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            title: const Text('TLS-Zertifikat prüfen'),
            subtitle: const Text('Deaktivieren für Self-Signed-Zertifikate'),
            value: _verifyTls,
            onChanged: (value) => setState(() => _verifyTls = value),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _testing ? null : _saveAndTest,
            icon: _testing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.check_circle),
            label: Text(_testing ? 'Teste Verbindung...' : 'Speichern & Testen'),
          ),
        ],
      ),
    );
  }
}
