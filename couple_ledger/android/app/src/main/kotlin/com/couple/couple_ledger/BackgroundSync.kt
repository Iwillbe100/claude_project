package com.couple.couple_ledger

import android.content.Context
import android.os.Handler
import android.os.Looper
import io.flutter.FlutterInjector
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.MethodChannel

/**
 * 카드 알림이 오면 앱이 꺼져 있어도 Flutter 엔진을 잠깐 띄워 Dart의 backgroundSync()를
 * 실행한다. Dart 쪽이 큐를 비우고 Firestore에 저장한 뒤 "done"을 호출하면 엔진을 끈다.
 */
object BackgroundSync {
    private const val CHANNEL = "couple_ledger/capture"
    private const val TIMEOUT_MS = 60_000L

    private val main = Handler(Looper.getMainLooper())
    private var engine: FlutterEngine? = null
    private var rerun = false
    private var appContext: Context? = null

    fun trigger(ctx: Context) {
        appContext = ctx.applicationContext
        main.post {
            // 동기화 중에 새 알림이 오면 끝난 뒤 한 번 더 돈다
            if (engine != null) {
                rerun = true
                return@post
            }
            val app = ctx.applicationContext
            val loader = FlutterInjector.instance().flutterLoader()
            loader.startInitialization(app)
            loader.ensureInitializationComplete(app, null)

            val e = FlutterEngine(app)
            MethodChannel(e.dartExecutor.binaryMessenger, CHANNEL)
                .setMethodCallHandler { call, result ->
                    when (call.method) {
                        "drain" -> result.success(CardNotificationService.drain(app))
                        "done" -> {
                            result.success(null)
                            finish(e)
                        }
                        else -> result.notImplemented()
                    }
                }
            engine = e
            e.dartExecutor.executeDartEntrypoint(
                DartExecutor.DartEntrypoint(loader.findAppBundlePath(), "backgroundSync")
            )
            main.postDelayed({ finish(e) }, TIMEOUT_MS)
        }
    }

    private fun finish(e: FlutterEngine) {
        if (engine !== e) return
        engine = null
        e.destroy()
        if (rerun) {
            rerun = false
            appContext?.let { trigger(it) }
        }
    }
}
