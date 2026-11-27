import 'package:flutter/material.dart';

void main() {
  runApp(const FintechSampleApp());
}

class FintechSampleApp extends StatelessWidget {
  final Map<String, bool> flags;

  const FintechSampleApp({
    super.key,
    this.flags = const {
      'instant_payouts': true,
      'biometric_checkout': true,
      'festival_launcher_icon': false,
    },
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NovaPay Fintech Sample',
      home: Scaffold(
        appBar: AppBar(title: const Text('NovaPay Wallet')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ListTile(
              title: const Text('Instant Payouts'),
              subtitle: Text(
                (flags['instant_payouts'] ?? false) ? 'Enabled' : 'Disabled',
              ),
            ),
            ListTile(
              title: const Text('Biometric Checkout'),
              subtitle: Text(
                (flags['biometric_checkout'] ?? false) ? 'Enabled' : 'Disabled',
              ),
            ),
            ListTile(
              title: const Text('Festival Launcher Icon'),
              subtitle: Text(
                (flags['festival_launcher_icon'] ?? false) ? 'Enabled' : 'Disabled',
              ),
            ),
          ],
        ),
      ),
    );
  }
}
