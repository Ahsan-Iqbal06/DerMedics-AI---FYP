import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../home/home_screen.dart';
import 'reports_screen.dart';

final reportProvider =
    FutureProvider.autoDispose.family<Report, int>((ref, id) => ref.watch(repositoryProvider).report(id));

/// Patient report, laid out like the downloadable PDF: patient card + photo, disease details with a confidence
/// ring, medicine tiles and dermatologist recommendations.
class ReportDetailScreen extends ConsumerWidget {
  const ReportDetailScreen({super.key, required this.id});
  final int id;

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete report?'),
        content: Text('This permanently removes the report and its analysis from your account.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text('Cancel')),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: context.c.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text('Delete'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref.read(repositoryProvider).deleteReport(id);
      ref.invalidate(reportsProvider);
      ref.invalidate(dashboardProvider);
      if (context.mounted) {
        showSnack(context, 'Report deleted');
        context.pop();
      }
    } on ApiException catch (e) {
      if (context.mounted) showSnack(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(reportProvider(id)).when(
          loading: () => PageScaffold(showBack: true, children: [LoadingView()]),
          error: (e, _) => PageScaffold(
            showBack: true,
            children: [ErrorView(message: e.toString(), onRetry: () => ref.invalidate(reportProvider(id)))],
          ),
          data: (r) {
            final a = r.analysis;
            return PageScaffold(
              showBack: true,
              children: [
                _ReportHeader(report: r),
                SizedBox(height: 12),
                _PatientCard(report: r),
                SizedBox(height: 12),
                _DiseaseDetails(analysis: a),
                if (a.isConclusive && a.medicines.isNotEmpty) ...[
                  SizedBox(height: 18),
                  _MedicineTiles(analysis: a),
                ],
                SizedBox(height: 14),
                _Recommendations(analysis: a),
                SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: () => downloadReportPdf(context, ref, r.id),
                  icon: Icon(Icons.download_rounded),
                  label: Text('Download PDF'),
                ),
                SizedBox(height: 8),
                TextButton.icon(
                  style: TextButton.styleFrom(foregroundColor: context.c.danger),
                  onPressed: () => _delete(context, ref),
                  icon: Icon(Icons.delete_outline_rounded),
                  label: Text('Delete report'),
                ),
                FootNote('AI findings are informational. Consult a clinician before treatment.'),
              ],
            );
          },
        );
  }
}

class _ReportHeader extends StatelessWidget {
  const _ReportHeader({required this.report});
  final Report report;

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    final created = report.createdAt;
    return Container(
      padding: EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: BoxDecoration(
        color: c.soft,
        borderRadius: BorderRadius.circular(18),
        border: Border(top: BorderSide(color: c.brand, width: 3)),
      ),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Spacer(),
              LogoMark(size: 52),
              Expanded(
                child: Text(
                  created == null
                      ? ''
                      : 'Date: ${DateFormat('dd/MM/yyyy').format(created)}\n${DateFormat('h:mm a').format(created)}',
                  textAlign: TextAlign.right,
                  style: TextStyle(color: c.muted, fontSize: 11.5, height: 1.4),
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          Text.rich(
            TextSpan(children: [
              TextSpan(text: 'DerMedics AI', style: TextStyle(color: c.brand)),
              TextSpan(text: ' - Patient report', style: TextStyle(color: c.text)),
            ]),
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _PatientCard extends StatelessWidget {
  const _PatientCard({required this.report});
  final Report report;

  @override
  Widget build(BuildContext context) {
    final a = report.analysis;
    final c = context.c;
    final rows = <(String, String)>[
      ('Name', report.subjectName),
      ('Report ID', 'DM-${report.id.toString().padLeft(6, '0')}'),
      if (report.subjectAge != null) ('Age', '${report.subjectAge}'),
      ('Relationship', report.relationship),
      if (a.bodyArea.isNotEmpty) ('Body area', a.bodyArea),
      if (a.region.isNotEmpty) ('Region', a.region),
    ];
    final info = AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Patient Personal Info', style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
          SizedBox(height: 10),
          for (final (k, v) in rows)
            Padding(
              padding: EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(width: 92, child: Text(k, style: TextStyle(color: c.muted, fontSize: 13))),
                  Expanded(child: Text(v, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
                ],
              ),
            ),
        ],
      ),
    );
    final photo = Column(
      children: [
        Container(
          padding: EdgeInsets.all(4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: c.brand, width: 2),
            color: c.surface,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: AuthImage(a.imageUrl, fallback: Center(child: IconBubble(Icons.image_outlined, size: 56))),
            ),
          ),
        ),
        SizedBox(height: 6),
        Text('Patient uploaded skin image', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      ],
    );
    // Side by side on tablets / web, stacked on phones.
    return LayoutBuilder(
      builder: (context, box) => box.maxWidth >= 560
          ? Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [Expanded(flex: 11, child: info), SizedBox(width: 12), Expanded(flex: 9, child: photo)],
            )
          : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [photo, SizedBox(height: 12), info]),
    );
  }
}

class _DiseaseDetails extends StatelessWidget {
  const _DiseaseDetails({required this.analysis});
  final Analysis analysis;

  @override
  Widget build(BuildContext context) {
    final a = analysis;
    final d = a.description;
    final c = context.c;
    final sections = <(String, List<String>)>[
      if (d != null) ...[
        ('Symptoms', d.symptoms),
        ('Causes & triggers', d.causes),
        ('Risk factors', d.riskFactors),
        ('Self-care & precautions', d.precautions),
      ],
    ].where((s) => s.$2.isNotEmpty).toList();
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Disease Details', style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
          SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              ConfidenceRing(value: a.isConclusive ? a.confidence : null, size: 104),
              SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      a.isConclusive ? (a.displayName ?? d?.name ?? 'Result') : 'Inconclusive result',
                      style: TextStyle(color: c.brand, fontSize: 17, fontWeight: FontWeight.w800),
                    ),
                    if (a.isDemo)
                      Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Text('Demo model output — illustrative only.',
                            style: TextStyle(color: c.amberText, fontSize: 12)),
                      ),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Text(
            a.isConclusive
                ? (d?.overview.isNotEmpty == true ? d!.overview : 'No description is available for this condition.')
                : 'The AI could not give a reliable result for this photo. The image may be unclear, or the condition '
                    'may not be one the model supports. No medicine suggestions are shown for uncertain results.',
            style: TextStyle(fontSize: 13.5, height: 1.5),
          ),
          if (a.isConclusive) ...[
            for (final (title, items) in sections) ...[
              SizedBox(height: 14),
              _SubTitle(title),
              ...items.map((i) => _Bullet(i)),
            ],
            if (d != null && d.outlook.isNotEmpty) ...[
              SizedBox(height: 14),
              _SubTitle('Outlook'),
              Text(d.outlook, style: TextStyle(fontSize: 13.5, height: 1.45)),
            ],
          ],
        ],
      ),
    );
  }
}

class _MedicineTiles extends StatelessWidget {
  const _MedicineTiles({required this.analysis});
  final Analysis analysis;

  // (background, icon) pairs; tinted to suit light and dark mode.
  static const _palette = [
    Color(0xFF3B5BDB),
    Color(0xFF2F9E6B),
    Color(0xFFC08A00),
    Color(0xFF6D3FD1),
    Color(0xFFC2417A),
  ];

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final meds = analysis.medicines.take(5).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('MEDICINE SUGGESTIONS',
            textAlign: TextAlign.center,
            style: TextStyle(color: context.c.deep, fontWeight: FontWeight.w800, letterSpacing: 1.1, fontSize: 13.5)),
        SizedBox(height: 10),
        LayoutBuilder(builder: (context, box) {
          final perRow = box.maxWidth >= 560 ? 4 : 2;
          final width = (box.maxWidth - 10 * (perRow - 1)) / perRow;
          return Wrap(
            alignment: WrapAlignment.center,
            spacing: 10,
            runSpacing: 10,
            children: [
              for (var i = 0; i < meds.length; i++)
                SizedBox(
                  width: width,
                  child: Material(
                    color: _palette[i % _palette.length].withValues(alpha: dark ? 0.22 : 0.12),
                    borderRadius: BorderRadius.circular(16),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => context.push('/analyze/result/${analysis.id}/medicines', extra: analysis),
                      child: Padding(
                        padding: EdgeInsets.fromLTRB(10, 12, 10, 12),
                        child: Column(
                          children: [
                            Icon(Icons.medication_rounded, color: _palette[i % _palette.length], size: 30),
                            SizedBox(height: 6),
                            Text(meds[i].name,
                                textAlign: TextAlign.center,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                            SizedBox(height: 2),
                            Text(
                              '${meds[i].type}${meds[i].type.isEmpty ? '' : ' · '}'
                              '${meds[i].prescriptionRequired ? 'Prescription' : 'OTC'}',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: context.c.muted, fontSize: 11.5),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        }),
        SizedBox(height: 6),
        Text('Tap a medicine for usage notes and cautions. Confirm with a pharmacist or doctor before use.',
            textAlign: TextAlign.center, style: TextStyle(color: context.c.muted, fontSize: 11.5)),
      ],
    );
  }
}

class _Recommendations extends StatelessWidget {
  const _Recommendations({required this.analysis});
  final Analysis analysis;

  @override
  Widget build(BuildContext context) {
    final a = analysis;
    final d = a.description;
    final items = a.isConclusive
        ? [if (d != null && d.whenToSeeDoctor.isNotEmpty) d.whenToSeeDoctor, ...?d?.dermatologistCare]
        : [
            'Book an in-person skin examination with a dermatologist.',
            'Take a clear, well-lit photo to show the doctor how the area has changed.',
            'Seek urgent care for rapid spreading, bleeding, fever or severe pain.',
          ];
    final doctors = a.dermatologists.take(3).toList();
    return AppCard(
      borderColor: context.c.brand,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Specialist Dermatologist Recommendations', style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
          SizedBox(height: 10),
          ...items.map((i) => _Bullet(i)),
          if (doctors.isNotEmpty) ...[
            SizedBox(height: 12),
            _SubTitle('Dermatologists you can contact'),
            for (final doc in doctors)
              _Bullet([doc.name, if (doc.clinic.isNotEmpty) doc.clinic, if (doc.city.isNotEmpty) doc.city, if (doc.phone.isNotEmpty) doc.phone]
                  .join(' • ')),
            SizedBox(height: 4),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => context.push('/analyze/result/${a.id}', extra: a),
                icon: Icon(Icons.local_hospital_outlined, size: 18),
                label: Text('Full analysis & all dermatologists'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SubTitle extends StatelessWidget {
  const _SubTitle(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(bottom: 4),
        child: Text(text, style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w700, fontSize: 13.5)),
      );
}

class _Bullet extends StatelessWidget {
  const _Bullet(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(bottom: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: EdgeInsets.only(top: 7, right: 8),
              child: Container(width: 5, height: 5, decoration: BoxDecoration(color: context.c.brand, shape: BoxShape.circle)),
            ),
            Expanded(child: Text(text, style: TextStyle(fontSize: 13.5, height: 1.45))),
          ],
        ),
      );
}

/// Donut chart of the model's confidence (deep purple → lilac), or a dash when there is no reliable result.
class ConfidenceRing extends StatelessWidget {
  const ConfidenceRing({super.key, required this.value, this.size = 100});
  final double? value;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _RingPainter(value ?? 0, track: c.border, colors: [c.deep, c.brand, c.accent]),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(value == null ? '—' : '${(value! * 100).round()}%',
                  style: TextStyle(fontSize: size * 0.21, fontWeight: FontWeight.w800, color: c.text)),
              Text('AI confidence', style: TextStyle(fontSize: size * 0.085, color: c.muted)),
            ],
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.value, {required this.track, required this.colors});
  final double value;
  final Color track;
  final List<Color> colors;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = size.width * 0.1;
    final rect = Offset.zero & size;
    final arcRect = rect.deflate(stroke / 2);
    canvas.drawArc(arcRect, 0, math.pi * 2, false,
        Paint()
          ..color = track
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke);
    if (value <= 0) return;
    final sweep = math.pi * 2 * value.clamp(0, 1);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: 0,
        endAngle: sweep,
        colors: colors,
        transform: GradientRotation(-math.pi / 2),
      ).createShader(rect);
    canvas.drawArc(arcRect, -math.pi / 2, sweep, false, paint);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.value != value || old.track != track || old.colors != colors;
}
