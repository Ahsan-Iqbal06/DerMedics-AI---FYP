import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/config.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';

/// Lets a phone point the app at the PC running the backend, e.g. 192.168.18.128:8000.
Future<void> showServerSettings(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _ServerSettingsSheet(),
    );

class _ServerSettingsSheet extends StatefulWidget {
  const _ServerSettingsSheet();

  @override
  State<_ServerSettingsSheet> createState() => _ServerSettingsSheetState();
}

class _ServerSettingsSheetState extends State<_ServerSettingsSheet> {
  late final TextEditingController _url = TextEditingController(text: AppConfig.baseUrl);
  bool _testing = false;
  String? _result;
  bool _ok = false;

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _test() async {
    final url = AppConfig.normalize(_url.text);
    if (url == null) return;
    setState(() {
      _testing = true;
      _result = null;
    });
    try {
      final res = await Dio(BaseOptions(connectTimeout: const Duration(seconds: 6), receiveTimeout: const Duration(seconds: 6)))
          .get('$url/api/health');
      final model = (res.data is Map) ? res.data['classifier'] : null;
      setState(() {
        _ok = true;
        _result = 'Connected${model != null ? ' • model $model' : ''}';
      });
    } catch (_) {
      setState(() {
        _ok = false;
        _result = 'Could not reach $url. Check the address, that your phone and PC are on the same Wi-Fi, '
            'and that Windows Firewall allows the server.';
      });
    } finally {
      if (mounted) setState(() => _testing = false);
    }
  }

  Future<void> _save() async {
    await AppConfig.setServerUrl(_url.text);
    if (mounted) {
      Navigator.pop(context);
      showSnack(context, 'Server set to ${AppConfig.baseUrl}');
    }
  }

  Future<void> _reset() async {
    await AppConfig.setServerUrl(null);
    if (mounted) {
      Navigator.pop(context);
      showSnack(context, 'Server reset to ${AppConfig.baseUrl}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return Padding(
      padding: EdgeInsets.fromLTRB(22, 0, 22, MediaQuery.viewInsetsOf(context).bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Server settings', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text(
            'Address of the computer running the DerMedics backend. On a phone, use your PC\'s Wi-Fi address, '
            'for example 192.168.18.128:8000.',
            style: TextStyle(color: c.muted, fontSize: 12.5, height: 1.4),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _url,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: const InputDecoration(labelText: 'Server address', prefixIcon: Icon(Icons.dns_outlined, size: 20)),
            onChanged: (_) => setState(() => _result = null),
          ),
          if (_result != null) ...[
            const SizedBox(height: 10),
            NoticeBox(
              tone: _ok ? BadgeTone.mint : BadgeTone.danger,
              icon: _ok ? Icons.check_circle_outline_rounded : Icons.error_outline_rounded,
              title: _ok ? 'Server reachable' : 'Not reachable',
              body: _result!,
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                  onPressed: _testing ? null : _test,
                  child: Text(_testing ? 'Testing…' : 'Test connection'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(child: FilledButton(onPressed: _save, child: const Text('Save'))),
            ],
          ),
          if (AppConfig.isCustom)
            TextButton(onPressed: _reset, child: Text('Reset to default (${AppConfig.defaultBaseUrl})')),
        ],
      ),
    );
  }
}
