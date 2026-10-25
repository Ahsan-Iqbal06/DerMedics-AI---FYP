import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../auth/auth_controller.dart';

typedef CareQuery = ({String country, String city, String q, double? lat, double? lng});

final dermatologistsProvider = FutureProvider.autoDispose.family<List<Dermatologist>, CareQuery>(
  (ref, q) => ref
      .watch(repositoryProvider)
      .dermatologists(country: q.country, city: q.city, query: q.q, lat: q.lat, lng: q.lng),
);

class CareScreen extends ConsumerStatefulWidget {
  const CareScreen({super.key});

  @override
  ConsumerState<CareScreen> createState() => _CareScreenState();
}

class _CareScreenState extends ConsumerState<CareScreen> {
  late final TextEditingController _country;
  late final TextEditingController _city;
  final _search = TextEditingController();
  Timer? _debounce;
  bool _mapView = false;
  bool _locating = false;
  Position? _position;
  late CareQuery _query;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authControllerProvider).user;
    _country = TextEditingController(text: user?.country ?? 'Pakistan');
    _city = TextEditingController(text: user?.city ?? '');
    _query = (country: _country.text, city: _city.text, q: '', lat: null, lng: null);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    for (final c in [_country, _city, _search]) {
      c.dispose();
    }
    super.dispose();
  }

  void _apply() {
    setState(() => _query = (
          country: _country.text.trim(),
          city: _position == null ? _city.text.trim() : '',
          q: _search.text.trim(),
          lat: _position?.latitude,
          lng: _position?.longitude,
        ));
  }

  void _debounced() {
    _debounce?.cancel();
    _debounce = Timer(Duration(milliseconds: 400), _apply);
  }

  /// Location is only requested here, after an explicit tap.
  Future<void> _useLocation() async {
    setState(() => _locating = true);
    try {
      if (!await Geolocator.isLocationServiceEnabled()) throw ApiException('Location services are turned off.');
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        throw ApiException('Location permission was not granted. You can still search by city.');
      }
      _position = await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(accuracy: LocationAccuracy.medium, timeLimit: Duration(seconds: 15)),
      );
      _apply();
      if (mounted) showSnack(context, 'Showing care options nearest to you');
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    } catch (_) {
      if (mounted) showSnack(context, 'Could not get your location. Try searching by city.');
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(dermatologistsProvider(_query));
    return PageScaffold(
      onRefresh: () => ref.refresh(dermatologistsProvider(_query).future),
      children: [
        PageTitle('Find nearby care', subtitle: 'Discover options for professional assessment.'),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Your search area', style: TextStyle(fontWeight: FontWeight.w700)),
              SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _country,
                      decoration: InputDecoration(labelText: 'Country'),
                      onSubmitted: (_) => _apply(),
                    ),
                  ),
                  SizedBox(width: 10),
                  Expanded(
                    child: TextField(
                      controller: _city,
                      decoration: InputDecoration(labelText: 'City / area'),
                      onChanged: (_) {
                        _position = null;
                        _debounced();
                      },
                      onSubmitted: (_) => _apply(),
                    ),
                  ),
                ],
              ),
              SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: TextButton.icon(
                  style: TextButton.styleFrom(
                    backgroundColor: context.c.soft.withValues(alpha: 0.6),
                    padding: EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: _locating ? null : _useLocation,
                  icon: _locating
                      ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : Icon(_position == null ? Icons.my_location_rounded : Icons.location_on_rounded, size: 18),
                  label: Text(_position == null ? 'Use my device location' : 'Using your location'),
                ),
              ),
            ],
          ),
        ),
        SizedBox(height: 12),
        TextField(
          controller: _search,
          onChanged: (_) => _debounced(),
          decoration: InputDecoration(
            hintText: 'Search specialty or clinic',
            prefixIcon: Icon(Icons.search_rounded, color: context.c.muted),
          ),
        ),
        SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: Segmented<bool>(
            options: {false: 'List', true: 'Map'},
            value: _mapView,
            onChanged: (v) => setState(() => _mapView = v),
          ),
        ),
        SectionHeader(
          'Dermatologists & clinics',
          trailing: results.whenOrNull(
            data: (r) => Text('${r.length} found', style: TextStyle(color: context.c.muted, fontSize: 12)),
          ),
        ),
        results.when(
          loading: () => LoadingView(),
          error: (e, _) =>
              ErrorView(message: e.toString(), onRetry: () => ref.invalidate(dermatologistsProvider(_query))),
          data: (items) {
            if (items.isEmpty) {
              return AppCard(
                child: Text('No providers found for this area. Try a nearby city or clear the search.',
                    style: TextStyle(color: context.c.muted, fontSize: 13)),
              );
            }
            if (_mapView) return _MapPreview(items: items);
            return Column(
              children: [
                for (final d in items) ...[ProviderCard(d), SizedBox(height: 10)],
              ],
            );
          },
        ),
        FootNote('Sample records are not verified. Confirm details and availability before visiting.'),
      ],
    );
  }
}

Uri mapsUri(Dermatologist d) {
  if (d.latitude != null && d.longitude != null) {
    return Uri.parse('https://www.google.com/maps/search/?api=1&query=${d.latitude},${d.longitude}');
  }
  final q = Uri.encodeComponent([d.name, d.address, d.city].where((s) => s.isNotEmpty).join(', '));
  return Uri.parse('https://www.google.com/maps/search/?api=1&query=$q');
}

class ProviderCard extends StatelessWidget {
  const ProviderCard(this.d, {super.key, this.highlightCondition});
  final Dermatologist d;
  final String? highlightCondition;

  @override
  Widget build(BuildContext context) {
    final treats = highlightCondition != null && d.conditions.contains(highlightCondition);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(d.isClinic ? Icons.local_hospital_outlined : Icons.favorite_border_rounded,
                  color: context.c.brand, size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(d.name, style: TextStyle(fontWeight: FontWeight.w700)),
                    SizedBox(height: 2),
                    Text(
                      [d.qualification, d.clinic != d.name ? d.clinic : ''].where((s) => s.isNotEmpty).join(' • '),
                      style: TextStyle(color: context.c.muted, fontSize: 12),
                    ),
                    SizedBox(height: 2),
                    Text(
                      [d.address, if (d.distanceKm != null) '${d.distanceKm} km away'].where((s) => s.isNotEmpty).join(' • '),
                      style: TextStyle(color: context.c.muted, fontSize: 12),
                    ),
                  ],
                ),
              ),
              if (d.rating != null)
                Row(children: [
                  Icon(Icons.star_rounded, size: 16, color: context.c.amberDot),
                  Text(d.rating!.toStringAsFixed(1), style: TextStyle(fontSize: 12)),
                ]),
            ],
          ),
          SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              if (d.isSample) StatusBadge('SAMPLE RECORD', tone: BadgeTone.neutral),
              if (d.source == 'google_places') StatusBadge('GOOGLE PLACES'),
              if (treats) StatusBadge('TREATS THIS CONDITION'),
            ],
          ),
          SizedBox(height: 6),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => launchUrl(mapsUri(d), mode: LaunchMode.externalApplication),
                icon: Icon(Icons.directions_outlined, size: 18),
                label: Text('Directions'),
              ),
              if (d.phone.isNotEmpty)
                TextButton.icon(
                  onPressed: () => launchUrl(Uri(scheme: 'tel', path: d.phone)),
                  icon: Icon(Icons.call_outlined, size: 18),
                  label: Text('Call'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Lightweight map substitute: plots providers by coordinates without needing a Maps API key.
class _MapPreview extends StatelessWidget {
  const _MapPreview({required this.items});
  final List<Dermatologist> items;

  @override
  Widget build(BuildContext context) {
    final located = items.where((d) => d.latitude != null && d.longitude != null).toList();
    if (located.isEmpty) {
      return AppCard(child: Text('No coordinates available for these providers.'));
    }
    final lats = located.map((d) => d.latitude!);
    final lngs = located.map((d) => d.longitude!);
    final minLat = lats.reduce((a, b) => a < b ? a : b), maxLat = lats.reduce((a, b) => a > b ? a : b);
    final minLng = lngs.reduce((a, b) => a < b ? a : b), maxLng = lngs.reduce((a, b) => a > b ? a : b);
    double norm(double v, double lo, double hi) => hi - lo < 1e-6 ? 0.5 : (v - lo) / (hi - lo);

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1.1,
          child: Container(
            decoration: BoxDecoration(
              color: context.c.soft.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: context.c.border),
            ),
            child: LayoutBuilder(builder: (context, c) {
              return Stack(
                children: [
                  for (final (i, d) in located.indexed)
                    Positioned(
                      left: 20 + norm(d.longitude!, minLng, maxLng) * (c.maxWidth - 60),
                      top: 20 + (1 - norm(d.latitude!, minLat, maxLat)) * (c.maxHeight - 60),
                      child: Tooltip(
                        message: d.name,
                        child: InkWell(
                          onTap: () => launchUrl(mapsUri(d), mode: LaunchMode.externalApplication),
                          child: CircleAvatar(
                            radius: 14,
                            backgroundColor: context.c.brand,
                            child: Text('${i + 1}', style: TextStyle(color: context.c.onBrand, fontSize: 11)),
                          ),
                        ),
                      ),
                    ),
                ],
              );
            }),
          ),
        ),
        SizedBox(height: 10),
        for (final (i, d) in located.indexed)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: CircleAvatar(
              radius: 12,
              backgroundColor: context.c.brand,
              child: Text('${i + 1}', style: TextStyle(color: context.c.onBrand, fontSize: 10)),
            ),
            title: Text(d.name, style: TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(d.city),
            trailing: Icon(Icons.open_in_new_rounded, size: 16, color: context.c.muted),
            onTap: () => launchUrl(mapsUri(d), mode: LaunchMode.externalApplication),
          ),
        FootNote('Live interactive maps require Google Maps/Places setup.'),
      ],
    );
  }
}
