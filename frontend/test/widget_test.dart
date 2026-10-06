import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:vietlott_ai/main.dart';
import 'package:vietlott_ai/providers/app_provider.dart';

void main() {
  testWidgets('home screen shows application title', (tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppProvider(autoLoad: false),
        child: const VietlottAiApp(),
      ),
    );

    expect(find.text('Vietlott AI'), findsOneWidget);
    expect(find.text('Tổng quan'), findsOneWidget);
  });
}
