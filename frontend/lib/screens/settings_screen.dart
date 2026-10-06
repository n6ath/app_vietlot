import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../widgets/app_card.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Cài đặt')),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isSmall = constraints.maxWidth < 360;
            return ListView(
              padding: EdgeInsets.all(isSmall ? 14 : 20),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Máy chủ API',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: provider.apiBaseUrl,
                        decoration: const InputDecoration(
                          labelText: 'Địa chỉ cơ sở',
                          prefixIcon: Icon(Icons.cloud_outlined),
                        ),
                        onChanged: provider.setApiBaseUrl,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                AppCard(
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Giao diện tối'),
                    subtitle: const Text('Sử dụng bảng màu tối'),
                    secondary: const Icon(Icons.dark_mode_outlined),
                    value: provider.isDarkMode,
                    onChanged: provider.setDarkMode,
                  ),
                ),
                const SizedBox(height: 12),
                const AppCard(
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.info_outline),
                    title: Text('Về Vietlott AI'),
                    subtitle: Text('Ứng dụng thống kê và phân tích Vietlott.'),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
