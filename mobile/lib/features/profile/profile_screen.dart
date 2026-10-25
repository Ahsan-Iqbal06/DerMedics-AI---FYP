import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/theme_mode.dart';
import '../../core/widgets.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_widgets.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  late final TextEditingController _country;
  late final TextEditingController _city;
  bool _savingRegion = false;
  bool _savingPhoto = false;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authControllerProvider).user;
    _country = TextEditingController(text: user?.country ?? '');
    _city = TextEditingController(text: user?.city ?? '');
  }

  @override
  void dispose() {
    _country.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _saveRegion() async {
    setState(() => _savingRegion = true);
    try {
      final user = await ref
          .read(repositoryProvider)
          .updateProfile(country: _country.text.trim(), city: _city.text.trim());
      ref.read(authControllerProvider.notifier).setUser(user);
      if (mounted) showSnack(context, 'Region updated');
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    } finally {
      if (mounted) setState(() => _savingRegion = false);
    }
  }

  Future<void> _editName() async {
    final user = ref.read(authControllerProvider).user;
    final ctrl = TextEditingController(text: user?.fullName);
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit profile details'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(labelText: 'Full name'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, ctrl.text.trim()), child: Text('Save')),
        ],
      ),
    );
    ctrl.dispose();
    if (name == null || name == user?.fullName) return;
    if (Validators.name(name) != null) {
      if (mounted) showSnack(context, 'Enter your full name');
      return;
    }
    try {
      final updated = await ref.read(repositoryProvider).updateProfile(fullName: name);
      ref.read(authControllerProvider.notifier).setUser(updated);
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    }
  }

  Future<void> _changePassword() async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _ChangePasswordSheet(),
    );
    if (changed == true && mounted) {
      showSnack(context, 'Password changed. Please sign in again.');
      await ref.read(authControllerProvider.notifier).logout();
    }
  }

  Future<void> _changePhoto() async {
    final hasPhoto = ref.read(authControllerProvider).user?.avatarUrl != null;
    final canUseCamera =
        !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS);
    final choice = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const IconBubble(Icons.photo_library_outlined, size: 36),
              title: const Text('Choose from gallery'),
              onTap: () => Navigator.pop(ctx, 'gallery'),
            ),
            if (canUseCamera)
              ListTile(
                leading: const IconBubble(Icons.photo_camera_outlined, size: 36),
                title: const Text('Take a photo'),
                onTap: () => Navigator.pop(ctx, 'camera'),
              ),
            if (hasPhoto)
              ListTile(
                leading: IconBubble(Icons.delete_outline_rounded, size: 36, color: ctx.c.dangerBg, iconColor: ctx.c.danger),
                title: Text('Remove photo', style: TextStyle(color: ctx.c.danger)),
                onTap: () => Navigator.pop(ctx, 'remove'),
              ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
    if (choice == null || !mounted) return;
    final repo = ref.read(repositoryProvider);
    try {
      if (choice == 'remove') {
        setState(() => _savingPhoto = true);
        ref.read(authControllerProvider.notifier).setUser(await repo.removeAvatar());
        if (mounted) showSnack(context, 'Profile photo removed');
        return;
      }
      final file = await ImagePicker().pickImage(
        source: choice == 'camera' ? ImageSource.camera : ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 90,
      );
      if (file == null) return;
      setState(() => _savingPhoto = true);
      final user = await repo.uploadAvatar(await file.readAsBytes(), file.name);
      ref.read(authControllerProvider.notifier).setUser(user);
      if (mounted) showSnack(context, 'Profile photo updated');
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    } finally {
      if (mounted) setState(() => _savingPhoto = false);
    }
  }

  Future<void> _clearLocal() async {
    final prefs = await SharedPreferences.getInstance();
    // Keep what the app needs to stay connected: the sign-in (stored here on the web) and the server address.
    const keep = {'access_token', 'refresh_token', 'server_url'};
    for (final key in prefs.getKeys().where((k) => !keep.contains(k)).toList()) {
      await prefs.remove(key);
    }
    await ref.read(themeModeProvider.notifier).set(ThemeMode.system);
    if (mounted) showSnack(context, 'Local app data cleared');
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).user;
    return PageScaffold(
      showBack: true,
      children: [
        PageTitle('Profile & settings', subtitle: 'Manage your preferences and privacy.'),
        _ProfileHeader(
          user: user,
          saving: _savingPhoto,
          onChangePhoto: _changePhoto,
          onEditName: _editName,
        ),
        SectionHeader('Your region', subtitle: 'Used for localized information only'),
        TextField(controller: _country, decoration: InputDecoration(labelText: 'Country')),
        SizedBox(height: 10),
        TextField(controller: _city, decoration: InputDecoration(labelText: 'City / area')),
        SizedBox(height: 10),
        OutlinedButton(
          style: OutlinedButton.styleFrom(minimumSize: Size.fromHeight(46)),
          onPressed: _savingRegion ? null : _saveRegion,
          child: Text(_savingRegion ? 'Saving…' : 'Save region'),
        ),
        const SectionHeader('Appearance', subtitle: 'Light, dark, or follow your device'),
        const _AppearancePicker(),
        const SectionHeader('Preferences', subtitle: 'Control how the app feels and behaves'),
        AppCard(
          child: _PrefRow(
            icon: Icons.my_location_rounded,
            title: 'Device location',
            body: 'Location is only requested after you tap "Use my location". Manual search is available.',
          ),
        ),
        SizedBox(height: 10),
        AppCard(
          onTap: _changePassword,
          child: _PrefRow(
            icon: Icons.lock_outline_rounded,
            title: 'Change password',
            body: 'Changing your password signs you out on all devices.',
          ),
        ),
        SizedBox(height: 10),
        AppCard(
          child: _PrefRow(
            icon: Icons.storage_rounded,
            title: 'Your data',
            body: 'Analyses and reports are stored under your account; sign-in tokens are kept in secure device storage.',
          ),
        ),
        SizedBox(height: 10),
        AppCard(
          color: context.c.dangerBg,
          borderColor: Colors.transparent,
          onTap: _clearLocal,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Clear local data', style: TextStyle(color: context.c.danger, fontWeight: FontWeight.w700)),
              SizedBox(height: 2),
              Text('Clears cached preferences on this device. Your saved reports are not affected.',
                  style: TextStyle(fontSize: 12)),
            ],
          ),
        ),
        SizedBox(height: 20),
        OutlinedButton.icon(
          style: OutlinedButton.styleFrom(
            minimumSize: Size.fromHeight(50),
            foregroundColor: context.c.danger,
          ),
          onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          icon: Icon(Icons.logout_rounded),
          label: Text('Sign out'),
        ),
      ],
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.user, required this.saving, required this.onChangePhoto, required this.onEditName});
  final AppUser? user;
  final bool saving;
  final VoidCallback onChangePhoto;
  final VoidCallback onEditName;

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 18),
      decoration: heroDecoration(context),
      child: Column(
        children: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              Semantics(
                button: true,
                label: 'Change profile photo',
                child: GestureDetector(onTap: saving ? null : onChangePhoto, child: UserAvatar(user: user, radius: 44)),
              ),
              if (saving)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.35), shape: BoxShape.circle),
                    child: Center(
                      child: SizedBox(
                        width: 26,
                        height: 26,
                        child: CircularProgressIndicator(strokeWidth: 2.6, color: c.onDeep),
                      ),
                    ),
                  ),
                ),
              Positioned(
                right: -2,
                bottom: -2,
                child: Material(
                  color: c.onDeep,
                  shape: const CircleBorder(),
                  elevation: 3,
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: saving ? null : onChangePhoto,
                    child: Padding(
                      padding: const EdgeInsets.all(7),
                      child: Icon(Icons.photo_camera_rounded, size: 18, color: c.deep),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(user?.fullName ?? '', style: TextStyle(color: c.onDeep, fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 2),
          Text(user?.email ?? '', style: TextStyle(color: c.onDeep.withValues(alpha: 0.75), fontSize: 12.5)),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: c.onDeep.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
            child: Text(
              'PATIENT ACCOUNT',
              style: TextStyle(color: c.accent, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.6),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 6,
            children: [
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: c.onDeep),
                onPressed: saving ? null : onChangePhoto,
                icon: const Icon(Icons.add_a_photo_outlined, size: 18),
                label: const Text('Change photo'),
              ),
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: c.onDeep),
                onPressed: onEditName,
                icon: const Icon(Icons.edit_outlined, size: 18),
                label: const Text('Edit name'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// System / Light / Dark choice, each with a small preview of its palette.
class _AppearancePicker extends ConsumerWidget {
  const _AppearancePicker();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeModeProvider);
    const options = [
      (ThemeMode.system, 'System', Icons.brightness_auto_rounded),
      (ThemeMode.light, 'Light', Icons.light_mode_rounded),
      (ThemeMode.dark, 'Dark', Icons.dark_mode_rounded),
    ];
    return Row(
      children: [
        for (final (i, (m, label, icon)) in options.indexed) ...[
          if (i > 0) const SizedBox(width: 10),
          Expanded(
            child: _ThemeOption(
              label: label,
              icon: icon,
              palette: switch (m) {
                ThemeMode.light => AppColors.light,
                ThemeMode.dark => AppColors.dark,
                ThemeMode.system => null,
              },
              selected: mode == m,
              onTap: () => ref.read(themeModeProvider.notifier).set(m),
            ),
          ),
        ],
      ],
    );
  }
}

class _ThemeOption extends StatelessWidget {
  const _ThemeOption({
    required this.label,
    required this.icon,
    required this.palette,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final IconData icon;

  /// Palette to preview; null shows light and dark side by side (System).
  final AppColors? palette;
  final bool selected;
  final VoidCallback onTap;

  Widget _swatch(AppColors p) => Container(
        decoration: BoxDecoration(
          color: p.canvas,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: p.border),
        ),
        padding: const EdgeInsets.all(6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 10,
              decoration: BoxDecoration(gradient: LinearGradient(colors: p.heroGradient), borderRadius: BorderRadius.circular(3)),
            ),
            const SizedBox(height: 4),
            Container(height: 5, width: 26, decoration: BoxDecoration(color: p.brand, borderRadius: BorderRadius.circular(3))),
            const SizedBox(height: 3),
            Container(height: 5, width: 18, decoration: BoxDecoration(color: p.accent, borderRadius: BorderRadius.circular(3))),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      decoration: BoxDecoration(
        color: selected ? c.soft : c.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: selected ? c.brand : c.border, width: selected ? 1.8 : 1),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            children: [
              SizedBox(
                height: 48,
                child: palette != null
                    ? _swatch(palette!)
                    : Row(children: [
                        Expanded(child: _swatch(AppColors.light)),
                        const SizedBox(width: 4),
                        Expanded(child: _swatch(AppColors.dark)),
                      ]),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 15, color: selected ? c.brand : c.muted),
                  const SizedBox(width: 4),
                  Text(
                    label,
                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: selected ? c.brand : c.text),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PrefRow extends StatelessWidget {
  const _PrefRow({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: context.c.brand, size: 20),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontWeight: FontWeight.w700)),
                SizedBox(height: 3),
                Text(body, style: TextStyle(color: context.c.muted, fontSize: 12.5, height: 1.4)),
              ],
            ),
          ),
        ],
      );
}

class _ChangePasswordSheet extends ConsumerStatefulWidget {
  const _ChangePasswordSheet();

  @override
  ConsumerState<_ChangePasswordSheet> createState() => _ChangePasswordSheetState();
}

class _ChangePasswordSheetState extends ConsumerState<_ChangePasswordSheet> {
  final _form = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _next = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref.read(repositoryProvider).changePassword(_current.text, _next.text);
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(22, 0, 22, MediaQuery.viewInsetsOf(context).bottom + 24),
      child: Form(
        key: _form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Change password', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            SizedBox(height: 14),
            if (_error != null) ErrorBanner(_error!),
            PasswordField(
              controller: _current,
              hint: 'Current password',
              validator: (v) => (v == null || v.isEmpty) ? 'Enter your current password' : null,
            ),
            SizedBox(height: 10),
            PasswordField(
              controller: _next,
              hint: 'New password',
              validator: Validators.strongPassword,
              onChanged: (_) => setState(() {}),
            ),
            PasswordChecklist(Validators.passwordChecks(_next.text)),
            SizedBox(height: 16),
            FilledButton(onPressed: _loading ? null : _submit, child: Text(_loading ? 'Saving…' : 'Update password')),
          ],
        ),
      ),
    );
  }
}
