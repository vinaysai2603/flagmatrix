import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_cubit.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_state.dart';
import 'package:flagmatrix_studio/presentation/screens/studio_screens.dart';

class StudioShell extends StatelessWidget {
  const StudioShell({super.key});

  static const _destinations = <(String, IconData)>[
    ('Connection', Icons.link),
    ('Workspace', Icons.workspaces_outline),
    ('Profiles', Icons.devices_other),
    ('Rules', Icons.rule_folder_outlined),
    ('Validate', Icons.play_circle_outline),
    ('Matrix', Icons.grid_on),
    ('Conflicts', Icons.warning_amber_outlined),
    ('Compare', Icons.compare_arrows),
    ('History', Icons.history),
    ('Export', Icons.download_outlined),
  ];

  static const _screens = <Widget>[
    ConnectionScreen(),
    WorkspaceScreen(),
    ProfilesScreen(),
    RulesScreen(),
    RunValidationScreen(),
    MatrixScreen(),
    ConflictsScreen(),
    CompareScreen(),
    HistoryScreen(),
    ExportScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StudioCubit, StudioState>(
      builder: (context, state) {
        return Scaffold(
          appBar: AppBar(
            title: const Text('FlagMatrix Studio'),
            actions: [
              if (state.loading)
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
            ],
          ),
          body: Column(
            children: [
              if (state.error != null)
                MaterialBanner(
                  content: Text(state.error!),
                  actions: [
                    TextButton(
                      onPressed: () =>
                          context.read<StudioCubit>().selectNav(state.navIndex),
                      child: const Text('Dismiss'),
                    ),
                  ],
                ),
              Expanded(
                child: Row(
                  children: [
                    LayoutBuilder(
                      builder: (context, constraints) => SingleChildScrollView(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(minHeight: constraints.maxHeight),
                          child: IntrinsicHeight(
                            child: NavigationRail(
                              selectedIndex: state.navIndex,
                              labelType: NavigationRailLabelType.all,
                              onDestinationSelected:
                                  context.read<StudioCubit>().selectNav,
                              destinations: _destinations
                                  .map(
                                    (d) => NavigationRailDestination(
                                      icon: Icon(d.$2),
                                      label: Text(d.$1),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const VerticalDivider(width: 1),
                    Expanded(child: _screens[state.navIndex]),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
