import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_cubit.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_state.dart';
import 'package:flagmatrix_studio/presentation/widgets/status_badge.dart';

/// Screen 1: Self-hosted Flagsmith connection.
class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key});

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  late final TextEditingController _apiCtrl;
  late final TextEditingController _fsCtrl;
  final _keyCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    final state = context.read<StudioCubit>().state;
    _apiCtrl = TextEditingController(text: state.apiBaseUrl);
    _fsCtrl = TextEditingController(text: state.flagsmithUrl);
  }

  @override
  void dispose() {
    _apiCtrl.dispose();
    _fsCtrl.dispose();
    _keyCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Self-Hosted Flagsmith Connection',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            const Text(
              'Connect to the FlagMatrix FastAPI adapter and your self-hosted Flagsmith instance. '
              'API keys stay in memory only and are redacted in logs.',
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _apiCtrl,
              decoration: const InputDecoration(
                labelText: 'FlagMatrix API URL',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _fsCtrl,
              decoration: const InputDecoration(
                labelText: 'Self-Hosted Flagsmith URL',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _keyCtrl,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Flagsmith Organisation Master API Key (optional if env set)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                FilledButton.icon(
                  onPressed: state.loading
                      ? null
                      : () => context.read<StudioCubit>().connect(
                            apiBaseUrl: _apiCtrl.text.trim(),
                            flagsmithUrl: _fsCtrl.text.trim(),
                            apiKey: _keyCtrl.text.trim(),
                          ),
                  icon: const Icon(Icons.link),
                  label: const Text('Connect & Load Workspace'),
                ),
                Chip(
                  label: Text(
                    state.connected
                        ? 'Connected (${state.flagsmithVersion ?? "ok"})'
                        : 'Disconnected',
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

/// Screen 2: Project and environment selection.
class WorkspaceScreen extends StatelessWidget {
  const WorkspaceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Project & Environment Selection',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 16),
            if (state.projects.isEmpty)
              const Text('Connect to Flagsmith first to load projects and environments.')
            else ...[
              DropdownButtonFormField<int>(
                initialValue: state.selectedProjectId,
                decoration: const InputDecoration(
                  labelText: 'Project',
                  border: OutlineInputBorder(),
                ),
                items: state.projects
                    .map((p) => DropdownMenuItem(value: p.id, child: Text('${p.name} (ID ${p.id})')))
                    .toList(),
                onChanged: (id) {
                  if (id != null) context.read<StudioCubit>().selectProject(id);
                },
              ),
              const SizedBox(height: 16),
              Text('Environments', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...state.environments.map(
                (env) {
                  final selected = env.name == state.selectedEnvironment;
                  return ListTile(
                    leading: Icon(
                      selected
                          ? Icons.radio_button_checked
                          : Icons.radio_button_unchecked,
                    ),
                    title: Text(env.name),
                    subtitle: Text('Environment ID: ${env.id}'),
                    selected: selected,
                    onTap: () =>
                        context.read<StudioCubit>().selectEnvironment(env.name),
                  );
                },
              ),
            ],
          ],
        );
      },
    );
  }
}

/// Screen 3: Application capability registry.
class ProfilesScreen extends StatelessWidget {
  const ProfilesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Application Capability Registry',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            if (state.profiles.isEmpty)
              const Text('No application profiles loaded yet.')
            else
              ...state.profiles.map(
                (p) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${p.tenantId} — ${p.appId} (${p.platform} v${p.appVersion})',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 6),
                        Text('SDK Versions: ${p.sdkVersions}'),
                        Text('Backend APIs: ${p.backendApiVersions}'),
                        Text('Native Resources: ${p.nativeResources}'),
                        Text('Device Capabilities: ${p.deviceCapabilities}'),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Screen 4: Feature requirement viewer.
class RulesScreen extends StatelessWidget {
  const RulesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Feature Requirement Rules',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            if (state.rules.isEmpty)
              const Text('No feature rules loaded yet.')
            else
              ...state.rules.map(
                (r) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    title: Text(r.featureName,
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(
                      '${r.constraints.length} constraints | requireEnabled=${r.requireEnabled}',
                    ),
                    children: r.constraints
                        .map(
                          (c) => ListTile(
                            dense: true,
                            title: Text('${c['id']} (${c['type']}: ${c['target']})'),
                            subtitle: Text(c.toString()),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Screen 5: Validation run configuration.
class RunValidationScreen extends StatelessWidget {
  const RunValidationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Validation Run Configuration',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 12),
              Text('Environment: ${state.selectedEnvironment}'),
              Text('Profiles loaded: ${state.profiles.length}'),
              Text('Rules loaded: ${state.rules.length}'),
              const SizedBox(height: 12),
              SwitchListTile(
                title: const Text('Strict Mode (block on UNKNOWN capabilities)'),
                value: state.strictMode,
                onChanged: context.read<StudioCubit>().setStrictMode,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: state.loading
                    ? null
                    : () => context.read<StudioCubit>().runValidation(),
                icon: const Icon(Icons.play_arrow),
                label: const Text('Run Compatibility Validation'),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Screen 6: Compatibility matrix.
class MatrixScreen extends StatelessWidget {
  const MatrixScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        final run = state.currentRun;
        if (run == null) {
          return const Center(child: Text('Run a validation first to view the compatibility matrix.'));
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Compatibility Matrix (${run.environment})',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              children: [
                Chip(label: Text('Total: ${run.totalChecks}')),
                Chip(label: Text('Supported: ${run.passed}')),
                Chip(label: Text('Incompatible: ${run.conflicts}')),
                Chip(label: Text('Unknown: ${run.unknowns}')),
                Chip(label: Text('Disabled: ${run.skipped}')),
                Chip(label: Text(run.blocking ? 'RELEASE BLOCKED' : 'RELEASE ALLOWED')),
              ],
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: const [
                  DataColumn(label: Text('Status')),
                  DataColumn(label: Text('Feature')),
                  DataColumn(label: Text('Identity')),
                  DataColumn(label: Text('Profile')),
                  DataColumn(label: Text('Rule')),
                ],
                rows: run.findings
                    .map(
                      (f) => DataRow(
                        onSelectChanged: (_) =>
                            context.read<StudioCubit>().inspectFinding(f),
                        cells: [
                          DataCell(StatusBadge(status: f.status)),
                          DataCell(Text(f.featureName)),
                          DataCell(Text(f.identity)),
                          DataCell(Text(f.profileId)),
                          DataCell(Text(f.ruleId)),
                        ],
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Screen 7: Conflict details.
class ConflictsScreen extends StatelessWidget {
  const ConflictsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        final conflicts = state.currentRun?.findings
                .where((f) =>
                    f.status == CompatibilityStatus.conflict ||
                    f.status == CompatibilityStatus.unknown)
                .toList() ??
            [];
        final selected = state.selectedFinding;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Conflict & Unknown Details',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            if (selected != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      StatusBadge(status: selected.status),
                      const SizedBox(height: 8),
                      Text('Feature: ${selected.featureName}',
                          style: Theme.of(context).textTheme.titleMedium),
                      Text('Identity: ${selected.identity}'),
                      Text('Profile: ${selected.profileId}'),
                      Text('Rule ID: ${selected.ruleId}'),
                      Text('Expected: ${selected.expectedRequirement}'),
                      Text('Observed: ${selected.observedCapability}'),
                      const SizedBox(height: 6),
                      Text('Explanation: ${selected.explanation}'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (conflicts.isEmpty)
              const Text('No conflicts or unknown capabilities in current run.')
            else
              ...conflicts.map(
                (f) => ListTile(
                  leading: StatusBadge(status: f.status),
                  title: Text('${f.featureName} — ${f.ruleId}'),
                  subtitle: Text('${f.profileId} (${f.identity})\n${f.explanation}'),
                  isThreeLine: true,
                  onTap: () => context.read<StudioCubit>().inspectFinding(f),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Screen 8: Environment comparison.
class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key});

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  String _source = 'Development';
  String _target = 'Production';

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        final envNames = state.environments.isEmpty
            ? ['Development', 'Production']
            : state.environments.map((e) => e.name).toList();
        if (!envNames.contains(_source)) _source = envNames.first;
        if (!envNames.contains(_target)) _target = envNames.last;

        final cmp = state.comparison;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Environment Comparison',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _source,
                    decoration: const InputDecoration(
                        labelText: 'Source', border: OutlineInputBorder()),
                    items: envNames
                        .map((n) => DropdownMenuItem(value: n, child: Text(n)))
                        .toList(),
                    onChanged: (v) => setState(() => _source = v ?? _source),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _target,
                    decoration: const InputDecoration(
                        labelText: 'Target', border: OutlineInputBorder()),
                    items: envNames
                        .map((n) => DropdownMenuItem(value: n, child: Text(n)))
                        .toList(),
                    onChanged: (v) => setState(() => _target = v ?? _target),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: state.loading
                      ? null
                      : () => context
                          .read<StudioCubit>()
                          .compareEnvironments(_source, _target),
                  child: const Text('Compare'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (cmp != null) ...[
              Text(
                '${cmp.sourceEnvironment} -> ${cmp.targetEnvironment}: '
                '${cmp.flagDiffs.length} flag diffs, '
                'new conflicts: ${cmp.newConflictsInTarget}, '
                'new unknowns: ${cmp.newUnknownsInTarget}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              ...cmp.flagDiffs.map(
                (d) => ListTile(
                  title: Text(d['feature_name'].toString()),
                  subtitle: Text(
                      '${cmp.sourceEnvironment}: enabled=${d['source_enabled']} | '
                      '${cmp.targetEnvironment}: enabled=${d['target_enabled']}'),
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}

/// Screen 9: Validation history.
class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Validation History',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            if (state.history.isEmpty)
              const Text('No validation runs recorded yet.')
            else
              ...state.history.map(
                (r) => Card(
                  child: ListTile(
                    title: Text('${r.environment} — ${r.runId.substring(0, 8)}'),
                    subtitle: Text(
                        'Pass: ${r.passed}, Conflicts: ${r.conflicts}, Unknown: ${r.unknowns}, Skipped: ${r.skipped}'),
                    trailing: Text(r.blocking ? 'BLOCKED' : 'PASS'),
                    onTap: () => context.read<StudioCubit>().selectHistoryRun(r),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Screen 10: Report export.
class ExportScreen extends StatelessWidget {
  const ExportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        final run = state.currentRun;
        return Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Report Export',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 12),
              if (run == null)
                const Text('Select or run a validation first to export its report.')
              else ...[
                Wrap(
                  spacing: 12,
                  children: [
                    FilledButton(
                      onPressed: () =>
                          context.read<StudioCubit>().loadExport('markdown'),
                      child: const Text('Export Markdown'),
                    ),
                    OutlinedButton(
                      onPressed: () =>
                          context.read<StudioCubit>().loadExport('json'),
                      child: const Text('Export JSON'),
                    ),
                    if (state.exportedReport.isNotEmpty)
                      TextButton.icon(
                        onPressed: () {
                          Clipboard.setData(
                              ClipboardData(text: state.exportedReport));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Report copied to clipboard')),
                          );
                        },
                        icon: const Icon(Icons.copy),
                        label: const Text('Copy'),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                Expanded(
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey.shade300),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SingleChildScrollView(
                      child: SelectableText(
                        state.exportedReport.isEmpty
                            ? 'Click Export Markdown or Export JSON above.'
                            : state.exportedReport,
                        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}
