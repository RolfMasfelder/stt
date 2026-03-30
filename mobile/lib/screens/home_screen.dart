import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/connection_status.dart';
import '../services/server_connection.dart';
import '../widgets/hal_eye.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  String _statusText(ConnectionStatus status) {
    switch (status) {
      case ConnectionStatus.disconnected:
        return 'Nicht verbunden';
      case ConnectionStatus.connected:
        return 'Verbunden';
      case ConnectionStatus.error:
        return 'Verbindungsfehler';
    }
  }

  @override
  Widget build(BuildContext context) {
    final connection = context.watch<ServerConnectionService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('STT'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.pushNamed(context, '/settings'),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            HalEye(
              status: connection.status,
              size: 200.0,
            ),
            const SizedBox(height: 32),
            Text(
              _statusText(connection.status),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: connection.status == ConnectionStatus.connected
                        ? Colors.green
                        : connection.status == ConnectionStatus.error
                            ? Colors.red
                            : Colors.grey,
                  ),
            ),
            if (connection.config != null) ...[
              const SizedBox(height: 8),
              Text(
                connection.config!.serverUrl,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
