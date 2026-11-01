import 'dart:typed_data';

import 'save_file_io.dart' if (dart.library.js_interop) 'save_file_web.dart' as impl;

/// Saves [bytes] as [filename] where the user can find it (Android Downloads, iPhone Files app, browser downloads),
/// opens it on phones, and returns a short description of where it was saved.
Future<String> saveAndOpenFile(Uint8List bytes, String filename) => impl.saveAndOpenFile(bytes, filename);
