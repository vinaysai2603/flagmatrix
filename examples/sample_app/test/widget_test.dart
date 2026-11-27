import 'package:flutter_test/flutter_test.dart';
import 'package:fintech_sample_app/main.dart';

void main() {
  testWidgets('Fintech sample renders flag-controlled features',
      (WidgetTester tester) async {
    await tester.pumpWidget(const FintechSampleApp());
    expect(find.text('NovaPay Wallet'), findsOneWidget);
    expect(find.text('Instant Payouts'), findsOneWidget);
    expect(find.text('Biometric Checkout'), findsOneWidget);
  });
}
