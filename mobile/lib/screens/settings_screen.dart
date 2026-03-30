import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/processing_config.dart';
import '../models/server_config.dart';
import '../models/connection_status.dart';
import '../services/auth.dart';
import '../services/processing_config.dart';
import '../services/server_connection.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;
  late TextEditingController _clientIdController;
  bool _verifyTls = true;
  bool _testing = false;

  // Processing config state
  late String _language;
  late String _model;
  late bool _diarize;
  late bool _summarize;
  late bool _structure;
  late String _audioFormat;
  late int _sampleRate;
  late bool _wifiOnly;
  late bool _autoUpload;

  @override
  void initState() {
    super.initState();
    final connection =
        Provider.of<ServerConnectionService>(context, listen: false);
    _urlController =
        TextEditingController(text: connection.config?.serverUrl ?? '');
    _clientIdController = TextEditingController();
    _verifyTls = connection.config?.verifyTls ?? true;

    final processing =
        Provider.of<ProcessingConfigService>(context, listen: false);
    final cfg = processing.config;
    _language = cfg.language;
    _model = cfg.model;
    _diarize = cfg.diarize;
    _summarize = cfg.summarize;
    _structure = cfg.structure;
    _audioFormat = cfg.audioFormat;
    _sampleRate = cfg.sampleRate;
    _wifiOnly = cfg.wifiOnly;
    _autoUpload = cfg.autoUpload;
  }

  @override
  void dispose() {
    _urlController.dispose();
    _clientIdController.dispose();
    super.dispose();
  }

  Future<void> _saveAndTest() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

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

  void _saveProcessingConfig() {
    final processing =
        Provider.of<ProcessingConfigService>(context, listen: false);
    processing.update(ProcessingConfig(
      language: _language,
      model: _model,
      diarize: _diarize,
      summarize: _summarize,
      structure: _structure,
      audioFormat: _audioFormat,
      sampleRate: _sampleRate,
      wifiOnly: _wifiOnly,
      autoUpload: _autoUpload,
    ));
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
          // --- Server Connection ---
          _sectionHeader('Server-Verbindung'),
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
            label:
                Text(_testing ? 'Teste Verbindung...' : 'Speichern & Testen'),
          ),
          const Divider(height: 48),

          // --- Authentication ---
          _sectionHeader('Authentifizierung'),
          const SizedBox(height: 16),
          _buildAuthSection(),
          const Divider(height: 48),
          _sectionHeader('Transkription'),
          const SizedBox(height: 16),
          _dropdownTile<String>(
            title: 'Sprache',
            subtitle: ProcessingConfig.languageLabels[_language] ?? _language,
            icon: Icons.language,
            value: _language,
            items: ProcessingConfig.availableLanguages
                .map((l) => DropdownMenuItem(
                      value: l,
                      child:
                          Text(ProcessingConfig.languageLabels[l] ?? l),
                    ))
                .toList(),
            onChanged: (v) {
              setState(() => _language = v!);
              _saveProcessingConfig();
            },
          ),
          _dropdownTile<String>(
            title: 'Whisper-Modell',
            subtitle:
                ProcessingConfig.modelDescriptions[_model] ?? _model,
            icon: Icons.model_training,
            value: _model,
            items: ProcessingConfig.availableModels
                .map((m) => DropdownMenuItem(
                      value: m,
                      child: Text(
                          '$m — ${ProcessingConfig.modelDescriptions[m]}'),
                    ))
                .toList(),
            onChanged: (v) {
              setState(() => _model = v!);
              _saveProcessingConfig();
            },
          ),
          const Divider(height: 48),

          // --- Processing Pipeline ---
          _sectionHeader('Verarbeitung'),
          const SizedBox(height: 8),
          SwitchListTile(
            title: const Text('Sprechererkennung'),
            subtitle: const Text('Sprecher automatisch zuordnen'),
            secondary: const Icon(Icons.people),
            value: _diarize,
            onChanged: (v) {
              setState(() => _diarize = v);
              _saveProcessingConfig();
            },
          ),
          SwitchListTile(
            title: const Text('Strukturierung'),
            subtitle: const Text('Text in Abschnitte gliedern'),
            secondary: const Icon(Icons.format_list_bulleted),
            value: _structure,
            onChanged: (v) {
              setState(() => _structure = v);
              _saveProcessingConfig();
            },
          ),
          SwitchListTile(
            title: const Text('Zusammenfassung'),
            subtitle: const Text('Automatische Zusammenfassung erstellen'),
            secondary: const Icon(Icons.summarize),
            value: _summarize,
            onChanged: (v) {
              setState(() => _summarize = v);
              _saveProcessingConfig();
            },
          ),
          const Divider(height: 48),

          // --- Audio ---
          _sectionHeader('Audio-Aufnahme'),
          const SizedBox(height: 16),
          _dropdownTile<String>(
            title: 'Audio-Format',
            subtitle:
                ProcessingConfig.audioFormatLabels[_audioFormat] ??
                    _audioFormat,
            icon: Icons.audio_file,
            value: _audioFormat,
            items: ProcessingConfig.availableAudioFormats
                .map((f) => DropdownMenuItem(
                      value: f,
                      child: Text(
                          ProcessingConfig.audioFormatLabels[f] ?? f),
                    ))
                .toList(),
            onChanged: (v) {
              setState(() => _audioFormat = v!);
              _saveProcessingConfig();
            },
          ),
          _dropdownTile<int>(
            title: 'Sample-Rate',
            subtitle:
                ProcessingConfig.sampleRateLabels[_sampleRate] ??
                    '$_sampleRate Hz',
            icon: Icons.graphic_eq,
            value: _sampleRate,
            items: ProcessingConfig.availableSampleRates
                .map((r) => DropdownMenuItem(
                      value: r,
                      child: Text(
                          ProcessingConfig.sampleRateLabels[r] ?? '$r Hz'),
                    ))
                .toList(),
            onChanged: (v) {
              setState(() => _sampleRate = v!);
              _saveProcessingConfig();
            },
          ),
          const Divider(height: 48),

          // --- Network ---
          _sectionHeader('Netzwerk'),
          const SizedBox(height: 8),
          SwitchListTile(
            title: const Text('Nur über WLAN'),
            subtitle: const Text('Upload nur bei WLAN-Verbindung'),
            secondary: const Icon(Icons.wifi),
            value: _wifiOnly,
            onChanged: (v) {
              setState(() => _wifiOnly = v);
              _saveProcessingConfig();
            },
          ),
          SwitchListTile(
            title: const Text('Automatischer Upload'),
            subtitle:
                const Text('Aufnahme nach Stopp automatisch hochladen'),
            secondary: const Icon(Icons.cloud_upload),
            value: _autoUpload,
            onChanged: (v) {
              setState(() => _autoUpload = v);
              _saveProcessingConfig();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildAuthSection() {
    final auth = context.watch<AuthService>();

    if (auth.isAuthenticated) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            leading: const Icon(Icons.check_circle, color: Colors.green),
            title: const Text('Angemeldet'),
            subtitle: Text(
              auth.state.expiresAt != null
                  ? 'Token gültig bis ${auth.state.expiresAt!.toLocal()}'
                  : 'Token aktiv',
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () async {
              await auth.logout();
              if (!mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Abgemeldet')),
              );
            },
            icon: const Icon(Icons.logout),
            label: const Text('Abmelden'),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _clientIdController,
          decoration: const InputDecoration(
            labelText: 'OAuth2 Client-ID',
            hintText: 'z.B. stt-mobile-app',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.key),
          ),
          autocorrect: false,
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: () => _login(auth),
          icon: const Icon(Icons.login),
          label: const Text('Anmelden'),
        ),
      ],
    );
  }

  Future<void> _login(AuthService auth) async {
    final url = _urlController.text.trim();
    final clientId = _clientIdController.text.trim();

    if (url.isEmpty || clientId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Server-URL und Client-ID eingeben'),
        ),
      );
      return;
    }

    final success = await auth.login(serverUrl: url, clientId: clientId);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          success ? 'Anmeldung erfolgreich' : 'Anmeldung fehlgeschlagen',
        ),
        backgroundColor:
            success ? Colors.green.shade800 : Colors.red.shade800,
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleLarge,
    );
  }

  Widget _dropdownTile<T>({
    required String title,
    required String subtitle,
    required IconData icon,
    required T value,
    required List<DropdownMenuItem<T>> items,
    required ValueChanged<T?> onChanged,
  }) {
    return ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right),
      onTap: () async {
        final result = await showDialog<T>(
          context: context,
          builder: (ctx) => SimpleDialog(
            title: Text(title),
            children: items
                .map((item) => SimpleDialogOption(
                      onPressed: () => Navigator.pop(ctx, item.value),
                      child: item.child,
                    ))
                .toList(),
          ),
        );
        if (result != null) {
          onChanged(result);
        }
      },
    );
  }
}
