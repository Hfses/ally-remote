package com.allyremote.app

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.wifi.WifiManager
import android.os.Bundle
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.cancel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.InetSocketAddress
import java.net.Socket

/**
 * Ally Remote — app Android.
 *
 * Tela inicial: digite o IP do Ally ou toque em "procurar" para o app
 * varrer a rede Wi-Fi atrás do servidor (porta 8765). Depois disso a
 * interface (servida pelo AllyRemote.exe rodando no Ally) abre em tela
 * cheia num WebView, e o IP fica salvo para as próximas vezes.
 *
 * Botão VOLTAR do Android: volta para a tela de conexão (trocar de IP);
 * apertando de novo, sai do app.
 */
class MainActivity : Activity() {

    companion object {
        const val PORT = 8765
        val BG = Color.parseColor("#0A0B0E")
        val PANEL = Color.parseColor("#13151B")
        val LINE = Color.parseColor("#252A35")
        val TXT = Color.parseColor("#EEF1F5")
        val DIM = Color.parseColor("#8B94A3")
        val RED = Color.parseColor("#FF4438")
    }

    private lateinit var web: WebView
    private lateinit var setup: LinearLayout
    private lateinit var ipEdit: EditText
    private lateinit var connectBtn: Button
    private lateinit var scanBtn: Button
    private lateinit var status: TextView
    private lateinit var backFab: TextView
    private val scope = MainScope()
    private val prefs by lazy { getSharedPreferences("allyremote", Context.MODE_PRIVATE) }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = BG
        window.navigationBarColor = BG

        val root = FrameLayout(this).apply { setBackgroundColor(BG) }

        // ---------- WebView (a interface vem do servidor no Ally) ----------
        web = WebView(this).apply {
            visibility = View.GONE
            setBackgroundColor(BG)
            keepScreenOn = true
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            webChromeClient = android.webkit.WebChromeClient()
            addJavascriptInterface(NativeBridge(), "AllyNative")
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(
                    view: WebView?, request: WebResourceRequest?, error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        val d = if (android.os.Build.VERSION.SDK_INT >= 23)
                            "${error?.errorCode}: ${error?.description}" else "erro"
                        showSetup("Não consegui abrir a página do Ally ($d).\n" +
                            "Confira: AllyRemote.exe aberto no Ally, mesmo Wi-Fi, e o IP certo.")
                    }
                }
            }
        }
        root.addView(web, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))

        // ---------- botão flutuante "trocar Ally / voltar à conexão" ----------
        backFab = TextView(this).apply {
            text = "⟲"
            visibility = View.GONE
            setTextColor(TXT)
            textSize = 20f
            gravity = Gravity.CENTER
            alpha = 0.55f
            background = GradientDrawable().apply {
                setColor(PANEL); cornerRadius = dp(20).toFloat(); setStroke(dp(1), LINE)
            }
            setOnClickListener { showSetup(null) }
        }
        root.addView(backFab, FrameLayout.LayoutParams(dp(40), dp(40)).apply {
            gravity = Gravity.TOP or Gravity.END
            topMargin = dp(8); rightMargin = dp(8)
        })

        // ---------- tela de conexão ----------
        setup = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(28), dp(28), dp(28), dp(28))
        }

        val logo = TextView(this).apply {
            val s = SpannableString("ALLY⟋⟋REMOTE")
            s.setSpan(ForegroundColorSpan(RED), 4, 6, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            text = s
            setTextColor(TXT)
            textSize = 26f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.14f
        }
        val sub = TextView(this).apply {
            text = "Controle o ROG Ally pelo celular.\nAbra o AllyRemote.exe no Ally e conecte:"
            setTextColor(DIM)
            textSize = 13f
            gravity = Gravity.CENTER
            setPadding(0, dp(10), 0, dp(26))
        }

        fun roundedBox(fill: Int, stroke: Int) = GradientDrawable().apply {
            setColor(fill); cornerRadius = dp(12).toFloat(); setStroke(dp(1), stroke)
        }

        ipEdit = EditText(this).apply {
            hint = "IP do Ally (ex.: 192.168.1.42)"
            setText(prefs.getString("ip", ""))
            setTextColor(TXT)
            setHintTextColor(DIM)
            textSize = 16f
            typeface = Typeface.MONOSPACE
            background = roundedBox(PANEL, LINE)
            setPadding(dp(16), dp(14), dp(16), dp(14))
            inputType = android.text.InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_GO
            setSingleLine(true)
            setOnEditorActionListener { _, _, _ -> tryConnectFromField(); true }
        }

        connectBtn = Button(this).apply {
            text = "CONECTAR"
            setTextColor(Color.WHITE)
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            background = roundedBox(RED, RED)
            setOnClickListener { tryConnectFromField() }
        }
        scanBtn = Button(this).apply {
            text = "🔍  PROCURAR O ALLY NA REDE"
            setTextColor(TXT)
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            background = roundedBox(PANEL, LINE)
            setOnClickListener { scan() }
        }
        status = TextView(this).apply {
            text = ""
            setTextColor(DIM)
            textSize = 12.5f
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, 0)
        }

        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        setup.addView(logo)
        setup.addView(sub)
        setup.addView(ipEdit, lp)
        setup.addView(connectBtn, LinearLayout.LayoutParams(lp).apply { topMargin = dp(12) })
        setup.addView(scanBtn, LinearLayout.LayoutParams(lp).apply { topMargin = dp(10) })
        setup.addView(status, lp)

        root.addView(setup, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.CENTER))

        setContentView(root)

        // Conecta direto se já tem IP salvo
        val saved = prefs.getString("ip", null)
        if (!saved.isNullOrBlank()) connect(saved) else showSetup(null)
    }

    private fun tryConnectFromField() {
        val ip = ipEdit.text.toString().trim()
        if (ip.isEmpty()) { status.text = "Digite o IP mostrado na janela do AllyRemote no Ally."; return }
        connect(ip)
    }

    private fun connect(ip: String) {
        scope.launch {
            setBusy(true)
            status.text = "Conectando em $ip…"
            val err = withContext(Dispatchers.IO) { probe(ip) }
            setBusy(false)
            if (err != null) { status.text = err; return@launch }
            prefs.edit().putString("ip", ip).apply()
            setup.visibility = View.GONE
            web.visibility = View.VISIBLE
            backFab.visibility = View.VISIBLE
            web.loadUrl("http://$ip:$PORT/")
        }
    }

    /** Testa se o servidor responde e devolve uma mensagem de erro clara (ou null se ok). */
    private fun probe(ip: String): String? {
        return try {
            val c = java.net.URL("http://$ip:$PORT/needs-pin").openConnection()
                as java.net.HttpURLConnection
            c.connectTimeout = 2500; c.readTimeout = 2500
            val code = c.responseCode
            c.disconnect()
            if (code in 200..499) null
            else "O Ally respondeu ($code) mas de forma inesperada. Baixe o AllyRemote.exe mais recente."
        } catch (e: java.net.SocketTimeoutException) {
            "Sem resposta de $ip:$PORT.\nO AllyRemote.exe está aberto no Ally? Celular no mesmo Wi-Fi? IP certo?"
        } catch (e: java.net.ConnectException) {
            "Conexão recusada em $ip:$PORT.\nAbra o AllyRemote.exe no Ally (ele libera o firewall sozinho na 1ª vez)."
        } catch (e: Exception) {
            "Falha ao conectar: ${e.message ?: e.javaClass.simpleName}"
        }
    }

    private fun showSetup(message: String?) {
        web.visibility = View.GONE
        backFab.visibility = View.GONE
        setup.visibility = View.VISIBLE
        if (message != null) status.text = message
    }

    private fun setBusy(busy: Boolean) {
        connectBtn.isEnabled = !busy
        scanBtn.isEnabled = !busy
        scanBtn.alpha = if (busy) 0.5f else 1f
    }

    /** Varre a sub-rede Wi-Fi atrás da porta 8765 aberta (o servidor no Ally). */
    private fun scan() {
        scope.launch {
            setBusy(true)
            status.text = "Procurando o Ally na rede Wi-Fi…"
            val prefix = subnetPrefix()
            if (prefix == null) {
                status.text = "Não detectei o Wi-Fi. Digite o IP manualmente."
                setBusy(false); return@launch
            }
            val found = withContext(Dispatchers.IO) {
                coroutineScope {
                    (1..254).map { i ->
                        async {
                            val host = "$prefix.$i"
                            try {
                                Socket().use { s -> s.connect(InetSocketAddress(host, PORT), 400) }
                                host
                            } catch (e: Exception) { null }
                        }
                    }.awaitAll().filterNotNull().firstOrNull()
                }
            }
            setBusy(false)
            if (found != null) {
                ipEdit.setText(found)
                status.text = "Ally encontrado em $found ✓"
                connect(found)
            } else {
                status.text = "Nenhum Ally encontrado.\nO AllyRemote.exe está aberto no Ally? Celular no mesmo Wi-Fi?"
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun subnetPrefix(): String? {
        val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val ip = wm.connectionInfo.ipAddress
        if (ip == 0) return null
        return "${ip and 0xff}.${(ip shr 8) and 0xff}.${(ip shr 16) and 0xff}"
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.visibility == View.VISIBLE) showSetup(null)
        else super.onBackPressed()
    }

    /** Ponte JS -> Android para tela cheia em paisagem (chamada pela interface web). */
    inner class NativeBridge {
        @android.webkit.JavascriptInterface
        fun enterFullscreen() { runOnUiThread { setImmersiveLandscape(true) } }

        @android.webkit.JavascriptInterface
        fun exitFullscreen() { runOnUiThread { setImmersiveLandscape(false) } }
    }

    @Suppress("DEPRECATION")
    private fun setImmersiveLandscape(on: Boolean) {
        requestedOrientation = if (on)
            android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        else
            android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        if (on) {
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
        } else {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE
        }
    }

    override fun onResume() {
        super.onResume()
        // Mantemos a WebView viva em segundo plano (não chamamos onPause) para
        // não travar. Ao voltar, só forçamos a reconexão do WebSocket.
        if (web.visibility == View.VISIBLE) {
            web.resumeTimers()
            web.evaluateJavascript("window.__reconnect && window.__reconnect();", null)
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
