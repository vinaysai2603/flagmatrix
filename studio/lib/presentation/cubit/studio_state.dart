import 'package:equatable/equatable.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';

class StudioState extends Equatable {
  final int navIndex;
  final bool loading;
  final String? error;
  final String apiBaseUrl;
  final String flagsmithUrl;
  final bool connected;
  final String? flagsmithVersion;
  final List<FlagsmithProjectInfo> projects;
  final int? selectedProjectId;
  final List<FlagsmithEnvInfo> environments;
  final String selectedEnvironment;
  final bool strictMode;
  final List<AppProfileEntity> profiles;
  final List<FeatureRuleEntity> rules;
  final ValidationRecordEntity? currentRun;
  final EvaluationFindingEntity? selectedFinding;
  final List<ValidationRecordEntity> history;
  final EnvComparisonEntity? comparison;
  final String exportedReport;
  final String exportFormat;

  const StudioState({
    this.navIndex = 0,
    this.loading = false,
    this.error,
    this.apiBaseUrl = 'http://localhost:8080',
    this.flagsmithUrl = 'http://localhost:8000',
    this.connected = false,
    this.flagsmithVersion,
    this.projects = const [],
    this.selectedProjectId,
    this.environments = const [],
    this.selectedEnvironment = 'Development',
    this.strictMode = false,
    this.profiles = const [],
    this.rules = const [],
    this.currentRun,
    this.selectedFinding,
    this.history = const [],
    this.comparison,
    this.exportedReport = '',
    this.exportFormat = 'markdown',
  });

  StudioState copyWith({
    int? navIndex,
    bool? loading,
    String? error,
    bool clearError = false,
    String? apiBaseUrl,
    String? flagsmithUrl,
    bool? connected,
    String? flagsmithVersion,
    List<FlagsmithProjectInfo>? projects,
    int? selectedProjectId,
    List<FlagsmithEnvInfo>? environments,
    String? selectedEnvironment,
    bool? strictMode,
    List<AppProfileEntity>? profiles,
    List<FeatureRuleEntity>? rules,
    ValidationRecordEntity? currentRun,
    EvaluationFindingEntity? selectedFinding,
    List<ValidationRecordEntity>? history,
    EnvComparisonEntity? comparison,
    String? exportedReport,
    String? exportFormat,
  }) {
    return StudioState(
      navIndex: navIndex ?? this.navIndex,
      loading: loading ?? this.loading,
      error: clearError ? null : (error ?? this.error),
      apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
      flagsmithUrl: flagsmithUrl ?? this.flagsmithUrl,
      connected: connected ?? this.connected,
      flagsmithVersion: flagsmithVersion ?? this.flagsmithVersion,
      projects: projects ?? this.projects,
      selectedProjectId: selectedProjectId ?? this.selectedProjectId,
      environments: environments ?? this.environments,
      selectedEnvironment: selectedEnvironment ?? this.selectedEnvironment,
      strictMode: strictMode ?? this.strictMode,
      profiles: profiles ?? this.profiles,
      rules: rules ?? this.rules,
      currentRun: currentRun ?? this.currentRun,
      selectedFinding: selectedFinding ?? this.selectedFinding,
      history: history ?? this.history,
      comparison: comparison ?? this.comparison,
      exportedReport: exportedReport ?? this.exportedReport,
      exportFormat: exportFormat ?? this.exportFormat,
    );
  }

  @override
  List<Object?> get props => [
        navIndex,
        loading,
        error,
        apiBaseUrl,
        flagsmithUrl,
        connected,
        flagsmithVersion,
        projects,
        selectedProjectId,
        environments,
        selectedEnvironment,
        strictMode,
        profiles,
        rules,
        currentRun,
        selectedFinding,
        history,
        comparison,
        exportedReport,
        exportFormat,
      ];
}
