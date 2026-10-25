import 'dart:typed_data';

import 'save_file_io.dart' if (dart.library.js_interop) 'save_file_web.dart' as impl;

/// Saves [bytes] as [filename] and opens it (mobile/desktop) or triggers a browser download (web).
Future<void> saveAndOpenFile(Uint8List bytes, String filename) => impl.saveAndOpenFile(bytes, filename);
