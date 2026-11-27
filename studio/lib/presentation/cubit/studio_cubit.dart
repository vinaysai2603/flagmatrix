import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';
import 'package:flagmatrix_studio/domain/repositories/flagmatrix_repository.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_state.dart';

class StudioCubit extends Cubit<StudioState> {
  final FlagMatrixRepository repository;

  StudioCubit(this.repository) : super(const StudioState());

  void selectNav(int index) => emit(state.copyWith(navIndex: index, clearError: true));

  void setStrictMode(bool strict) => emit(state.copyWith(strictMode: strict));

  void selectEnvironment(String envName) =>
      emit(state.copyWith(selectedEnvironment: envName));

  void inspectFinding(EvaluationFindingEntity finding) {
    emit(state.copyWith(selectedFinding: finding, navIndex: 6));
  }

  Future<void> connect({
    required String apiBaseUrl,
    required String flagsmithUrl,
    String? apiKey,
  }) async {
    emit(state.copyWith(loading: true, clearError: true, apiBaseUrl: apiBaseUrl, flagsmithUrl: flagsmithUrl));
    repository.setApiBaseUrl(apiBaseUrl);
    try {
      final conn = await repository.updateFlagsmithConnection(
        url: flagsmithUrl,
        apiKey: apiKey,
      );
      final projects = await repository.getProjects();
      final projectId = projects.isNotEmpty ? projects.first.id : 1;
      final envs = await repository.getEnvironments(projectId);
      final profiles = await repository.getProfiles();
      final rules = await repository.getRules();
      final history = await repository.getHistory();

      emit(state.copyWith(
        loading: false,
        connected: (conn['connected'] as bool?) ?? true,
        flagsmithVersion: conn['version'] as String?,
        projects: projects,
        selectedProjectId: projectId,
        environments: envs,
        selectedEnvironment: envs.isNotEmpty ? envs.first.name : 'Development',
        profiles: profiles,
        rules: rules,
        history: history,
      ));
    } catch (e) {
      emit(state.copyWith(loading: false, connected: false, error: e.toString()));
    }
  }

  Future<void> selectProject(int projectId) async {
    emit(state.copyWith(loading: true, clearError: true, selectedProjectId: projectId));
    try {
      final envs = await repository.getEnvironments(projectId);
      emit(state.copyWith(
        loading: false,
        environments: envs,
        selectedEnvironment: envs.isNotEmpty ? envs.first.name : state.selectedEnvironment,
      ));
    } catch (e) {
      emit(state.copyWith(loading: false, error: e.toString()));
    }
  }

  Future<void> runValidation() async {
    final projectId = state.selectedProjectId ?? 1;
    emit(state.copyWith(loading: true, clearError: true));
    try {
      final record = await repository.runValidation(
        projectId: projectId,
        environment: state.selectedEnvironment,
        strict: state.strictMode,
      );
      final history = await repository.getHistory();
      final firstConflict = record.findings
          .where((f) => f.status == CompatibilityStatus.conflict)
          .firstOrNull;
      emit(state.copyWith(
        loading: false,
        currentRun: record,
        selectedFinding: firstConflict,
        history: history,
        navIndex: 5,
      ));
    } catch (e) {
      emit(state.copyWith(loading: false, error: e.toString()));
    }
  }

  Future<void> compareEnvironments(String source, String target) async {
    final projectId = state.selectedProjectId ?? 1;
    emit(state.copyWith(loading: true, clearError: true));
    try {
      final cmp = await repository.compareEnvironments(
        projectId: projectId,
        sourceEnvironment: source,
        targetEnvironment: target,
        strict: state.strictMode,
      );
      emit(state.copyWith(loading: false, comparison: cmp));
    } catch (e) {
      emit(state.copyWith(loading: false, error: e.toString()));
    }
  }

  Future<void> loadExport(String format) async {
    final run = state.currentRun;
    if (run == null) return;
    emit(state.copyWith(loading: true, clearError: true, exportFormat: format));
    try {
      final content = await repository.exportReport(runId: run.runId, format: format);
      emit(state.copyWith(loading: false, exportedReport: content));
    } catch (e) {
      emit(state.copyWith(loading: false, error: e.toString()));
    }
  }

  void selectHistoryRun(ValidationRecordEntity record) {
    emit(state.copyWith(currentRun: record, navIndex: 5));
  }
}
