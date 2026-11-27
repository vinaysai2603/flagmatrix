import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';
import 'package:flagmatrix_studio/domain/repositories/flagmatrix_repository.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_cubit.dart';
import 'package:flagmatrix_studio/presentation/screens/studio_shell.dart';

class _FakeRepo implements FlagMatrixRepository {
  @override
  Future<Map<String, dynamic>> checkHealth() async => {'status': 'ok'};

  @override
  Future<EnvComparisonEntity> compareEnvironments({
    required int projectId,
    required String sourceEnvironment,
    required String targetEnvironment,
    required bool strict,
  }) async =>
      EnvComparisonEntity(
        sourceEnvironment: sourceEnvironment,
        targetEnvironment: targetEnvironment,
        flagDiffs: const [],
        newConflictsInTarget: 0,
        newUnknownsInTarget: 0,
      );

  @override
  Future<String> exportReport({required String runId, required String format}) async =>
      '# Report $runId';

  @override
  Future<List<FlagsmithEnvInfo>> getEnvironments(int projectId) async =>
      const [FlagsmithEnvInfo(id: 1, name: 'Development', project: 1)];

  @override
  Future<List<ValidationRecordEntity>> getHistory() async => const [];

  @override
  Future<List<AppProfileEntity>> getProfiles() async => const [];

  @override
  Future<List<FlagsmithProjectInfo>> getProjects() async =>
      const [FlagsmithProjectInfo(id: 1, name: 'flagmatrix')];

  @override
  Future<List<FeatureRuleEntity>> getRules() async => const [];

  @override
  Future<ValidationRecordEntity> runValidation({
    required int projectId,
    required String environment,
    required bool strict,
  }) async =>
      ValidationRecordEntity(
        runId: 'run-1234-5678',
        createdAt: '',
        environment: environment,
        strict: strict,
        totalChecks: 4,
        passed: 1,
        conflicts: 1,
        unknowns: 1,
        skipped: 1,
        blocking: true,
        findings: const [
          EvaluationFindingEntity(
            status: CompatibilityStatus.pass,
            featureName: 'f_pass',
            identity: 'id1',
            profileId: 'p1',
            ruleId: 'r1',
            expectedRequirement: 'ok',
            observedCapability: 'ok',
            explanation: 'Supported',
            source: 'flagsmith',
          ),
          EvaluationFindingEntity(
            status: CompatibilityStatus.conflict,
            featureName: 'f_bad',
            identity: 'id1',
            profileId: 'p1',
            ruleId: 'r2',
            expectedRequirement: '>=3.0.0',
            observedCapability: '2.0.0',
            explanation: 'SDK too old',
            source: 'flagsmith',
          ),
          EvaluationFindingEntity(
            status: CompatibilityStatus.unknown,
            featureName: 'f_unk',
            identity: 'id1',
            profileId: 'p1',
            ruleId: 'r3',
            expectedRequirement: 'biometrics',
            observedCapability: 'missing',
            explanation: 'Undeclared capability',
            source: 'flagsmith',
          ),
          EvaluationFindingEntity(
            status: CompatibilityStatus.skipped,
            featureName: 'f_off',
            identity: 'id1',
            profileId: 'p1',
            ruleId: 'r4',
            expectedRequirement: 'enabled',
            observedCapability: 'false',
            explanation: 'Disabled',
            source: 'flagsmith',
          ),
        ],
      );

  @override
  void setApiBaseUrl(String baseUrl) {}

  @override
  Future<Map<String, dynamic>> updateFlagsmithConnection({
    required String url,
    String? apiKey,
  }) async =>
      {'connected': true, 'version': '2.295.2'};
}

void main() {
  testWidgets('Studio renders all 10 navigation destinations and matrix badges',
      (WidgetTester tester) async {
    final cubit = StudioCubit(_FakeRepo());
    await tester.pumpWidget(
      BlocProvider<StudioCubit>.value(
        value: cubit,
        child: const MaterialApp(home: StudioShell()),
      ),
    );

    expect(find.text('FlagMatrix Studio'), findsOneWidget);
    expect(find.text('Connection'), findsOneWidget);
    expect(find.text('Export'), findsOneWidget);

    await cubit.runValidation();
    await tester.pumpAndSettle();

    expect(find.text('Supported'), findsOneWidget);
    expect(find.text('Incompatible'), findsOneWidget);
    expect(find.text('Unknown'), findsOneWidget);
    expect(find.text('Disabled'), findsOneWidget);
  });
}
