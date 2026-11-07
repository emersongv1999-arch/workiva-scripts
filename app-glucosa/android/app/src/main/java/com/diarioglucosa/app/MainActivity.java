package com.diarioglucosa.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import androidx.webkit.WebViewAssetLoader;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Diario de Glucosa: muestra la app web (assets/www) en un WebView a pantalla completa.
 * La página se sirve desde https://appassets.androidplatform.net para que sea un origen
 * seguro. El puente "AndroidBridge" guarda los datos en un archivo interno, exporta
 * archivos con el selector del sistema y copia texto al portapapeles.
 */
public class MainActivity extends Activity {

    private static final String HOST = "appassets.androidplatform.net";
    private static final String START_URL = "https://" + HOST + "/assets/www/index.html";
    private static final String STATE_FILE = "state.json";
    private static final int REQ_SAVE = 1;
    private static final int REQ_OPEN = 2;

    private final Object stateLock = new Object();
    private WebView web;
    private WebViewAssetLoader assetLoader;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingSave;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(getColor(R.color.app_bg));
        web = new WebView(this);
        web.setBackgroundColor(getColor(R.color.app_bg));
        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        setupSystemBars(root);

        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain(HOST)
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);

        web.addJavascriptInterface(new Bridge(), "AndroidBridge");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (HOST.equals(uri.getHost())) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (ActivityNotFoundException ignored) {
                }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(i, REQ_OPEN);
                    return true;
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    return false;
                }
            }
        });

        web.loadUrl(START_URL);
    }

    /** Pantalla de borde a borde: el contenido evita las barras del sistema y el teclado. */
    private void setupSystemBars(View root) {
        if (Build.VERSION.SDK_INT < 30) return;
        getWindow().setDecorFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            Insets b = insets.getInsets(WindowInsets.Type.systemBars()
                    | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
            v.setPadding(b.left, b.top, b.right, b.bottom);
            return WindowInsets.CONSUMED;
        });
        boolean night = (getResources().getConfiguration().uiMode
                & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        WindowInsetsController c = getWindow().getInsetsController();
        if (c != null) {
            int mask = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
            c.setSystemBarsAppearance(night ? 0 : mask, mask);
        }
    }

    private void toastInPage(String msg) {
        web.evaluateJavascript("window.__appToast&&window.__appToast(" + JSONObject.quote(msg) + ")", null);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        Uri uri = (resultCode == RESULT_OK && data != null) ? data.getData() : null;
        if (requestCode == REQ_OPEN) {
            if (fileCallback != null) {
                fileCallback.onReceiveValue(uri != null ? new Uri[]{uri} : null);
                fileCallback = null;
            }
        } else if (requestCode == REQ_SAVE) {
            String content = pendingSave;
            pendingSave = null;
            if (uri == null || content == null) return;
            try (OutputStream os = getContentResolver().openOutputStream(uri, "w")) {
                if (os == null) throw new IOException("sin destino");
                os.write(content.getBytes(StandardCharsets.UTF_8));
                toastInPage("Archivo guardado");
            } catch (Exception e) {
                toastInPage("No se pudo guardar el archivo.");
            }
        }
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        web.evaluateJavascript("(window.__appBack&&window.__appBack())?'1':'0'", value -> {
            if (!"\"1\"".equals(value)) finish();
        });
    }

    @Override
    protected void onPause() {
        web.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }

    /** Métodos que la página puede llamar como window.AndroidBridge.*. */
    private class Bridge {

        @JavascriptInterface
        public boolean saveState(String json) {
            synchronized (stateLock) {
                File dir = getFilesDir();
                File tmp = new File(dir, STATE_FILE + ".tmp");
                try (FileOutputStream os = new FileOutputStream(tmp)) {
                    os.write(json.getBytes(StandardCharsets.UTF_8));
                    os.getFD().sync();
                } catch (IOException e) {
                    return false;
                }
                return tmp.renameTo(new File(dir, STATE_FILE));
            }
        }

        @JavascriptInterface
        public String loadState() {
            synchronized (stateLock) {
                File f = new File(getFilesDir(), STATE_FILE);
                if (!f.exists()) return "";
                try (InputStream in = new FileInputStream(f)) {
                    ByteArrayOutputStream out = new ByteArrayOutputStream();
                    byte[] buf = new byte[16384];
                    int n;
                    while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                    return out.toString("UTF-8");
                } catch (IOException e) {
                    return "";
                }
            }
        }

        @JavascriptInterface
        public void saveFile(String name, String mime, String content) {
            runOnUiThread(() -> {
                pendingSave = content;
                Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType(mime == null || mime.isEmpty() ? "application/octet-stream" : mime);
                i.putExtra(Intent.EXTRA_TITLE, name);
                try {
                    startActivityForResult(i, REQ_SAVE);
                } catch (ActivityNotFoundException e) {
                    pendingSave = null;
                    toastInPage("No se encontró dónde guardar el archivo.");
                }
            });
        }

        @JavascriptInterface
        public void copyText(String text) {
            runOnUiThread(() -> {
                ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("Diario de Glucosa", text));
            });
        }
    }
}
