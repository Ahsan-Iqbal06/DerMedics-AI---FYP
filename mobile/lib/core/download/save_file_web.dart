import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// Triggers a normal browser download (the PC's Downloads folder) and returns where it went.
Future<String> saveAndOpenFile(Uint8List bytes, String filename) async {
  final blob = web.Blob([bytes.toJS].toJS, web.BlobPropertyBag(type: 'application/pdf'));
  final url = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..download = filename
    ..style.display = 'none';
  web.document.body!.append(anchor);
  anchor.click();
  anchor.remove();
  // Revoking straight away can cancel the download in some browsers (Firefox, Safari).
  Timer(const Duration(seconds: 30), () => web.URL.revokeObjectURL(url));
  return 'your Downloads folder';
}
