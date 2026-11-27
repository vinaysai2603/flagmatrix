import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flagmatrix_studio/core/di/service_locator.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_cubit.dart';
import 'package:flagmatrix_studio/presentation/screens/studio_shell.dart';

void main() {
  setupServiceLocator();
  runApp(const FlagMatrixStudioApp());
}

class FlagMatrixStudioApp extends StatelessWidget {
  const FlagMatrixStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<StudioCubit>(
      create: (_) => sl<StudioCubit>(),
      child: MaterialApp(
        title: 'FlagMatrix Studio',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1A73E8)),
          useMaterial3: true,
        ),
        home: const StudioShell(),
      ),
    );
  }
}
