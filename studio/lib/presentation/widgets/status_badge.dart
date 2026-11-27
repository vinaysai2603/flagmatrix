import 'package:flutter/material.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';

class StatusBadge extends StatelessWidget {
  final CompatibilityStatus status;

  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (Color bg, Color fg, IconData icon, String text) = switch (status) {
      CompatibilityStatus.pass => (
          const Color(0xFFE6F4EA),
          const Color(0xFF137333),
          Icons.check_circle_outline,
          'Supported',
        ),
      CompatibilityStatus.conflict => (
          const Color(0xFFFCE8E6),
          const Color(0xFFC5221F),
          Icons.error_outline,
          'Incompatible',
        ),
      CompatibilityStatus.unknown => (
          const Color(0xFFFEF7E0),
          const Color(0xFFB06000),
          Icons.help_outline,
          'Unknown',
        ),
      CompatibilityStatus.skipped => (
          const Color(0xFFF1F3F4),
          const Color(0xFF5F6368),
          Icons.block_outlined,
          'Disabled',
        ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: fg.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: fg),
          const SizedBox(width: 6),
          Text(
            text,
            style: TextStyle(color: fg, fontWeight: FontWeight.w600, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
