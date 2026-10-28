package com.couple.couple_ledger

import android.app.Notification
import android.content.Context
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONArray
import org.json.JSONObject

/**
 * 카드 결제 알림만 골라 큐에 저장한다. 앱이 꺼져 있어도 동작하고,
 * Flutter 쪽이 앱 실행/복귀 시 큐를 비우며 파싱한다.
 * 카드 결제로 보이지 않는 알림(대화 등)은 저장하지 않는다.
 */
class CardNotificationService : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName !in SOURCES) return
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString() ?: ""
        val body = if (title.isEmpty()) text else "$title\n$text"
        // 삼성월렛은 "₩3,500 결제 완료" / 가맹점 형식이라 "원"과 카드사가 없다
        if (sbn.packageName == SAMSUNG_WALLET) {
            if (!WALLET_PAYMENT.containsMatchIn(title) || text.isEmpty()) return
        } else if (sbn.packageName == TOSS) {
            // 토스는 송금/혜택 알림이 많아서 "9650원 결제" 카드 알림과
            // 토스증권 "MSTW 배당금 입금" 알림만 받는다
            val dividend = TOSS_DIVIDEND.containsMatchIn(title) && text.isNotEmpty()
            if (!dividend && !(TOSS_PAYMENT.containsMatchIn(title) && looksLikeCardPayment(body))) return
        } else if (!looksLikeCardPayment(body)) return
        enqueue(this, body, sbn.postTime)
        BackgroundSync.trigger(applicationContext)
    }

    companion object {
        private const val PREFS = "card_capture"
        private const val KEY = "pending"
        private const val MAX = 200

        private const val TOSS = "viva.republica.toss"
        private val TOSS_DIVIDEND = Regex("배당금\\s*입금")
        private val TOSS_PAYMENT = Regex("^[\\d,]+\\s*원\\s*(결제|승인)")

        private const val SAMSUNG_WALLET = "com.samsung.android.spay"
        private val WALLET_PAYMENT = Regex("^[₩\\\\]\\s*[\\d,]+\\s*(결제|승인)")

        // 카카오톡, 삼성/구글 메시지 앱, 토스, 삼성월렛
        private val SOURCES = setOf(
            "com.kakao.talk",
            "com.samsung.android.messaging",
            "com.google.android.apps.messaging",
            TOSS,
            SAMSUNG_WALLET,
        )
        private val ISSUERS = listOf("삼성", "현대", "신한", "KB", "국민", "우리", "하나", "롯데", "NH", "농협", "BC", "카드")
        private val AMOUNT = Regex("[\\d,]+\\s*원")

        fun looksLikeCardPayment(body: String): Boolean =
            AMOUNT.containsMatchIn(body) &&
                (body.contains("승인") || body.contains("결제")) &&
                ISSUERS.any { body.contains(it) }

        @Synchronized
        fun enqueue(ctx: Context, body: String, postTime: Long) {
            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val arr = JSONArray(prefs.getString(KEY, "[]"))
            // 같은 알림이 갱신되며 중복 전달되는 경우 방지
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                if (o.getLong("t") == postTime && o.getString("b") == body) return
            }
            arr.put(JSONObject().put("t", postTime).put("b", body))
            val trimmed = JSONArray()
            for (i in maxOf(0, arr.length() - MAX) until arr.length()) trimmed.put(arr.get(i))
            prefs.edit().putString(KEY, trimmed.toString()).apply()
        }

        @Synchronized
        fun drain(ctx: Context): List<Map<String, Any>> {
            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val arr = JSONArray(prefs.getString(KEY, "[]"))
            val out = (0 until arr.length()).map {
                val o = arr.getJSONObject(it)
                mapOf<String, Any>("time" to o.getLong("t"), "body" to o.getString("b"))
            }
            prefs.edit().putString(KEY, "[]").apply()
            return out
        }
    }
}
