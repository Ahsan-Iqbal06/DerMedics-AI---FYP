import 'dart:io';

import 'package:flutter/services.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

const _downloads = MethodChannel('dermedics/downloads');

/// Saves the file where the user can find it again, opens it, and returns where it was saved.
/// - Android: Downloads/DerMedics AI (shown in Files → Downloads).
/// - iPhone: the app's Documents folder, shown in Files → On My iPhone → DerMedics AI.
Future<String> saveAndOpenFile(Uint8List bytes, String filename) async {
  final dir = await getApplicationDocumentsDirectory();
  final file = File('${dir.path}${Platform.pathSeparator}$filename');
  await file.writeAsBytes(bytes, flush: true);

  var savedTo = Platform.isIOS ? 'Files › On My iPhone › DerMedics AI' : file.path;
  if (Platform.isAndroid) {
    try {
      savedTo = await _downloads.invokeMethod<String>('saveToDownloads', {'name': filename, 'bytes': bytes}) ?? savedTo;
    } on PlatformException catch (e) {
      // Still opened below from the app's own copy; tell the user it isn't in Downloads.
      savedTo = e.code == 'denied' ? 'the app only (storage permission was declined)' : 'the app only';
    }
  }
  await OpenFilex.open(file.path);
  return savedTo;
}
