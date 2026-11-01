package com.dermedics.dermedics_ai

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.media.MediaScannerConnection
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

/** Adds "save to the phone's Downloads folder" for report PDFs (channel: dermedics/downloads). */
class MainActivity : FlutterActivity() {
    private val folder = "DerMedics AI"
    private var pending: Triple<String, ByteArray, MethodChannel.Result>? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dermedics/downloads").setMethodCallHandler { call, result ->
            if (call.method != "saveToDownloads") return@setMethodCallHandler result.notImplemented()
            val name = call.argument<String>("name")!!
            val bytes = call.argument<ByteArray>("bytes")!!
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                save(name, bytes, result)
            } else if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED) {
                save(name, bytes, result)
            } else {
                // Android 9 and older need storage permission to write to the shared Downloads folder.
                pending = Triple(name, bytes, result)
                requestPermissions(arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), STORAGE_REQUEST)
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != STORAGE_REQUEST) return
        val (name, bytes, result) = pending ?: return
        pending = null
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) save(name, bytes, result)
        else result.error("denied", "Storage permission was not granted", null)
    }

    private fun save(name: String, bytes: ByteArray, result: MethodChannel.Result) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) saveWithMediaStore(name, bytes) else saveLegacy(name, bytes)
            result.success("Download/$folder/$name")
        } catch (e: Exception) {
            result.error("save_failed", e.message, null)
        }
    }

    /** Android 10+: no permission needed; the file appears in Files → Downloads → DerMedics AI. */
    private fun saveWithMediaStore(name: String, bytes: ByteArray) {
        val resolver = contentResolver
        val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
        val relativePath = "${Environment.DIRECTORY_DOWNLOADS}/$folder/"
        // Re-downloading the same report replaces the earlier copy instead of creating "name (1).pdf".
        val existing = resolver.query(
            collection, arrayOf(MediaStore.MediaColumns._ID),
            "${MediaStore.MediaColumns.DISPLAY_NAME}=? AND ${MediaStore.MediaColumns.RELATIVE_PATH}=?",
            arrayOf(name, relativePath), null,
        )?.use { c -> if (c.moveToFirst()) android.content.ContentUris.withAppendedId(collection, c.getLong(0)) else null }
        val uri = existing ?: resolver.insert(collection, ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, name)
            put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf")
            put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
        }) ?: throw IllegalStateException("Could not create the file in Downloads")
        resolver.openOutputStream(uri, "wt")!!.use { it.write(bytes) }
    }

    @Suppress("DEPRECATION")
    private fun saveLegacy(name: String, bytes: ByteArray) {
        val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), folder)
        dir.mkdirs()
        val file = File(dir, name)
        file.writeBytes(bytes)
        MediaScannerConnection.scanFile(this, arrayOf(file.absolutePath), arrayOf("application/pdf"), null)
    }

    companion object {
        private const val STORAGE_REQUEST = 4107
    }
}
