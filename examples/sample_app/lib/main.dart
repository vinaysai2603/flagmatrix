import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const FintechSampleApp());
}

class FlagsmithSampleService {
  final String baseUrl;
  final String environmentKey;
  final http.Client client;

  FlagsmithSampleService({
    required this.baseUrl,
    required this.environmentKey,
    http.Client? client,
  }) : client = client ?? http.Client();

  Future<Map<String, bool>> fetchIdentityFlags({
    required String identifier,
    required String tenantId,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/identities/');
    final resp = await client.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'X-Environment-Key': environmentKey,
      },
      body: jsonEncode({
        'identifier': identifier,
        'traits': [
          {'trait_key': 'tenant_id', 'trait_value': tenantId},
        ],
      }),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Flagsmith error ${resp.statusCode}: ${resp.body}');
    }
    final decoded = jsonDecode(resp.body) as Map<String, dynamic>;
    final rawFlags = decoded['flags'] as List<dynamic>? ?? const [];
    final result = <String, bool>{};
    for (final item in rawFlags) {
      final map = item as Map<String, dynamic>;
      final feature = map['feature'] as Map<String, dynamic>?;
      final name = feature?['name'] as String?;
      if (name != null) {
        result[name] = (map['enabled'] as bool?) ?? false;
      }
    }
    return result;
  }
}

class FintechSampleApp extends StatefulWidget {
  final FlagsmithSampleService? service;
  final String initialTenant;

  const FintechSampleApp({
    super.key,
    this.service,
    this.initialTenant = 'aurelia',
  });

  @override
  State<FintechSampleApp> createState() => _FintechSampleAppState();
}

class _FintechSampleAppState extends State<FintechSampleApp> {
  final _envKeyCtrl = TextEditingController();
  final _urlCtrl = TextEditingController(text: 'http://localhost:8000');
  late String _tenant;
  Map<String, bool> _flags = const {};
  String? _status;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _tenant = widget.initialTenant;
    if (widget.service != null) {
      _loadFlags(widget.service!);
    }
  }

  @override
  void dispose() {
    _envKeyCtrl.dispose();
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadFlags(FlagsmithSampleService svc) async {
    setState(() {
      _loading = true;
      _status = null;
    });
    try {
      final fetched = await svc.fetchIdentityFlags(
        identifier: '${_tenant}_sample_app',
        tenantId: _tenant,
      );
      setState(() {
        _flags = fetched;
        _loading = false;
        _status = 'Loaded ${fetched.length} flags from Flagsmith for $_tenant';
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _status = 'Error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FlagMatrix Fintech Sample',
      home: Scaffold(
        appBar: AppBar(title: const Text('FlagMatrix Fintech Sample')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (widget.service == null) ...[
              TextField(
                controller: _urlCtrl,
                decoration: const InputDecoration(
                  labelText: 'Flagsmith URL',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _envKeyCtrl,
                decoration: const InputDecoration(
                  labelText: 'Flagsmith Environment Client Key',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
            ],
            Row(
              children: [
                DropdownButton<String>(
                  value: _tenant,
                  items: const [
                    DropdownMenuItem(value: 'novapay', child: Text('novapay')),
                    DropdownMenuItem(value: 'aurelia', child: Text('aurelia')),
                    DropdownMenuItem(value: 'kinetix', child: Text('kinetix')),
                  ],
                  onChanged: (v) => setState(() => _tenant = v ?? _tenant),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _loading
                      ? null
                      : () {
                          final svc = widget.service ??
                              FlagsmithSampleService(
                                baseUrl: _urlCtrl.text.trim(),
                                environmentKey: _envKeyCtrl.text.trim(),
                              );
                          _loadFlags(svc);
                        },
                  child: const Text('Fetch Flagsmith Flags'),
                ),
              ],
            ),
            if (_status != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(_status!),
              ),
            const Divider(),
            for (final name in const [
              'instant_payouts',
              'biometric_checkout',
              'festival_launcher_icon',
              'legacy_pin_flow',
            ])
              ListTile(
                title: Text(name),
                trailing: Text((_flags[name] ?? false) ? 'Enabled' : 'Disabled'),
              ),
          ],
        ),
      ),
    );
  }
}
