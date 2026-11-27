import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:fintech_sample_app/main.dart';

void main() {
  testWidgets('Fintech sample fetches identity flags from Flagsmith API',
      (WidgetTester tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/api/v1/identities/');
      expect(request.headers['X-Environment-Key'], 'synth_client_key');
      return http.Response(
        jsonEncode({
          'flags': [
            {
              'feature': {'name': 'instant_payouts'},
              'enabled': true,
            },
            {
              'feature': {'name': 'biometric_checkout'},
              'enabled': true,
            },
            {
              'feature': {'name': 'festival_launcher_icon'},
              'enabled': false,
            },
          ],
        }),
        200,
      );
    });

    final service = FlagsmithSampleService(
      baseUrl: 'http://localhost:8000',
      environmentKey: 'synth_client_key',
      client: mockClient,
    );

    await tester.pumpWidget(FintechSampleApp(service: service));
    await tester.pumpAndSettle();

    expect(find.text('FlagMatrix Fintech Sample'), findsOneWidget);
    expect(find.text('Loaded 3 flags from Flagsmith for aurelia'), findsOneWidget);
    expect(find.text('Enabled'), findsNWidgets(2));
    expect(find.text('Disabled'), findsNWidgets(2));
  });
}
