import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../home/home_screen.dart';

const bodyAreas = [
  'Face / neck',
  'Scalp',
  'Arms / hands',
  'Chest / back',
  'Abdomen',
  'Legs / feet',
  'Groin / skin folds',
  'Other',
];

const _maxBytes = 10 * 1024 * 1024;

class UploadScreen extends ConsumerStatefulWidget {
  const UploadScreen({super.key});

  @override
  ConsumerState<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends ConsumerState<UploadScreen> {
  final _symptoms = TextEditingController();
  Uint8List? _bytes;
  String _filename = 'skin.jpg';
  String _bodyArea = bodyAreas.first;
  bool _consent = false;
  bool _loading = false;

  @override
  void dispose() {
    _symptoms.dispose();
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    final file = await ImagePicker().pickImage(source: source, maxWidth: 2048, imageQuality: 92);
    if (file == null) return;
    final ext = file.name.split('.').last.toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'webp'].contains(ext)) {
      if (mounted) showSnack(context, 'Please choose a JPG, PNG or WEBP image.');
      return;
    }
    final bytes = await file.readAsBytes();
    if (bytes.length > _maxBytes) {
      if (mounted) showSnack(context, 'That image is larger than 10 MB.');
      return;
    }
    setState(() {
      _bytes = bytes;
      _filename = file.name;
    });
  }

  void _choosePhoto() {
    final canUseCamera = !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS);
    if (!canUseCamera) {
      _pick(ImageSource.gallery);
      return;
    }
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: IconBubble(Icons.photo_library_outlined, size: 36),
              title: Text('Choose from gallery'),
              onTap: () {
                Navigator.pop(ctx);
                _pick(ImageSource.gallery);
              },
            ),
            ListTile(
              leading: IconBubble(Icons.photo_camera_outlined, size: 36),
              title: Text('Take a photo'),
              onTap: () {
                Navigator.pop(ctx);
                _pick(ImageSource.camera);
              },
            ),
            SizedBox(height: 12),
          ],
        ),
      ),
    );
  }

  Future<void> _analyze() async {
    if (_bytes == null) {
      showSnack(context, 'Add a skin photo first.');
      return;
    }
    if (!_consent) {
      showSnack(context, 'Please confirm you understand this is informational.');
      return;
    }
    setState(() => _loading = true);
    try {
      final analysis = await ref.read(repositoryProvider).analyze(
            bytes: _bytes!,
            filename: _filename,
            bodyArea: _bodyArea,
            symptoms: _symptoms.text.trim(),
          );
      ref.invalidate(dashboardProvider);
      if (!mounted) return;
      setState(() {
        _bytes = null;
        _consent = false;
        _symptoms.clear();
      });
      context.push('/analyze/result/${analysis.id}', extra: analysis);
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ready = _bytes != null && _consent && !_loading;
    return PageScaffold(
      children: [
        PageTitle("Let's look closer", subtitle: 'Upload a clear photo of the affected skin.'),
        AppCard(
          color: context.c.soft.withValues(alpha: 0.45),
          borderColor: context.c.brand.withValues(alpha: 0.35),
          onTap: _loading ? null : _choosePhoto,
          child: _bytes == null
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.upload_rounded, color: context.c.brand),
                    SizedBox(height: 8),
                    Text('Add a skin photo', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                    SizedBox(height: 4),
                    Text('Use good lighting and avoid filters. Choose a photo from your gallery.',
                        style: TextStyle(color: context.c.muted, fontSize: 12.5, height: 1.4)),
                    SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: _loading ? null : _choosePhoto,
                      child: Text('Choose photo'),
                    ),
                  ],
                )
              : Column(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: AspectRatio(aspectRatio: 4 / 3, child: Image.memory(_bytes!, fit: BoxFit.cover)),
                    ),
                    SizedBox(height: 10),
                    Row(
                      children: [
                        Icon(Icons.check_circle_rounded, color: context.c.brand, size: 18),
                        SizedBox(width: 6),
                        Expanded(
                          child: Text(_filename,
                              overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                        TextButton(onPressed: _loading ? null : _choosePhoto, child: Text('Change')),
                      ],
                    ),
                  ],
                ),
        ),
        Padding(
          padding: EdgeInsets.only(top: 8, left: 4),
          child: Text('JPG, PNG or WEBP • Up to 10 MB', style: TextStyle(color: context.c.muted, fontSize: 11.5)),
        ),
        SectionHeader('AI skin analysis',
            subtitle: 'The model analyzes the uploaded image and returns a likely condition.'),
        Row(
          children: [
            Expanded(child: _ModeChip(label: 'Analyze uploaded photo', selected: true)),
            SizedBox(width: 10),
            Expanded(child: _ModeChip(label: 'Inconclusive', selected: false)),
          ],
        ),
        SectionHeader('A few details'),
        DropdownButtonFormField<String>(
          initialValue: _bodyArea,
          decoration: InputDecoration(labelText: 'Body area'),
          items: [for (final a in bodyAreas) DropdownMenuItem(value: a, child: Text(a))],
          onChanged: _loading ? null : (v) => setState(() => _bodyArea = v ?? _bodyArea),
        ),
        SizedBox(height: 12),
        TextField(
          controller: _symptoms,
          enabled: !_loading,
          maxLines: 3,
          maxLength: 500,
          decoration: InputDecoration(
            labelText: 'What have you noticed?',
            hintText: 'Redness, texture or irritation…',
            alignLabelWithHint: true,
          ),
        ),
        AppCard(
          padding: EdgeInsets.fromLTRB(4, 4, 12, 4),
          onTap: _loading ? null : () => setState(() => _consent = !_consent),
          child: Row(
            children: [
              Checkbox(value: _consent, onChanged: _loading ? null : (v) => setState(() => _consent = v ?? false)),
              Expanded(
                child: Text('I understand this is informational, not a medical diagnosis.',
                    style: TextStyle(fontSize: 13)),
              ),
            ],
          ),
        ),
        SizedBox(height: 16),
        FilledButton(
          onPressed: ready ? _analyze : null,
          child: _loading
              ? Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand)),
                    SizedBox(width: 12),
                    Text('Analyzing…'),
                  ],
                )
              : Text('Analyze skin image'),
        ),
        FootNote('Seek medical care for severe or rapidly spreading symptoms.'),
      ],
    );
  }
}

/// Shows the two possible outcomes of the analysis, matching the spec's radio pair.
class _ModeChip extends StatelessWidget {
  const _ModeChip({required this.label, required this.selected});
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        color: context.c.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: selected ? context.c.brand : context.c.border, width: selected ? 1.6 : 1),
      ),
      child: Row(
        children: [
          Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off,
              size: 18, color: selected ? context.c.brand : context.c.muted),
          SizedBox(width: 8),
          Expanded(child: Text(label, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }
}
