/**
 * NaukriLoginWebView
 * Mirrors the Python Selenium bot's login flow using a real browser WebView:
 *   1. Open https://www.naukri.com/nlogin/login
 *   2. Auto-fill username + password (using React native-value setter, same as _type_into)
 *   3. Click the login button
 *   4. Detect successful login (URL changes away from /nlogin)
 *   5. Extract the auth token from localStorage / cookies
 *   6. Report back via onSuccess / onError
 */
import React, { useRef, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Modal,
} from 'react-native';
import { WebView, WebViewNavigation } from 'react-native-webview';
import { C } from '../theme';
import { storeToken } from '../services/naukri';

const LOGIN_URL = 'https://www.naukri.com/nlogin/login';

// ── JavaScript injected after page load to fill + submit the form ─────────────
// Same technique as the Python bot's _type_into() method:
// uses the native HTML input value setter so React form state updates.
function buildFillScript(email: string, password: string): string {
  return `
(function() {
  function setVal(el, val) {
    try {
      var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, val);
      el.dispatchEvent(new Event('input',  { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } catch(e) {
      el.value = val;
    }
  }

  var attempts = 0;
  var iv = setInterval(function() {
    attempts++;
    if (attempts > 50) { clearInterval(iv); return; }

    var email   = document.getElementById('usernameField')
                  || document.querySelector('input[placeholder*="Email" i]')
                  || document.querySelector('input[type="email"]')
                  || document.querySelector('input[type="text"]');
    var pwd     = document.getElementById('passwordField')
                  || document.querySelector('input[type="password"]');
    var btn     = document.querySelector('button[type="submit"]')
                  || document.querySelector('.loginButton')
                  || document.querySelector('[class*="login" i][class*="btn" i]');

    if (email && pwd) {
      clearInterval(iv);
      setVal(email, ${JSON.stringify(email)});
      setTimeout(function() {
        setVal(pwd, ${JSON.stringify(password)});
        setTimeout(function() {
          if (btn) {
            btn.click();
          } else {
            pwd.form && pwd.form.submit();
          }
        }, 400);
      }, 300);
    }
  }, 200);
})();
true;
`;
}

// ── Script injected after login URL change to extract the auth token ──────────
const EXTRACT_TOKEN_SCRIPT = `
(function() {
  var result = { token: null, cookies: document.cookie, ls: {} };
  try {
    // Walk all localStorage keys looking for JWT or authToken
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      var v = localStorage.getItem(k);
      result.ls[k] = v;
      if (!result.token && v && (v.startsWith('eyJ') || k.toLowerCase().indexOf('token') >= 0 || k.toLowerCase().indexOf('auth') >= 0)) {
        result.token = v;
      }
    }
  } catch(e) { result.lsError = e.message; }
  window.ReactNativeWebView.postMessage(JSON.stringify(result));
})();
true;
`;

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  email:     string;
  password:  string;
  onSuccess: (token: string) => void;
  onError:   (msg: string)   => void;
  onClose:   ()              => void;
}

export default function NaukriLoginWebView({ email, password, onSuccess, onError, onClose }: Props) {
  const wvRef              = useRef<WebView>(null);
  const [status, setStatus] = useState('Loading Naukri login page…');
  const [filled, setFilled] = useState(false);
  const loginDone           = useRef(false);

  const handleLoadEnd = useCallback(() => {
    if (!filled) {
      setFilled(true);
      setStatus('Filling in credentials…');
      wvRef.current?.injectJavaScript(buildFillScript(email, password));
    }
  }, [email, password, filled]);

  const handleNavigationChange = useCallback((nav: WebViewNavigation) => {
    const url = nav.url ?? '';
    if (!loginDone.current && !url.includes('/nlogin/')) {
      loginDone.current = true;
      setStatus('Logged in — extracting session token…');
      wvRef.current?.injectJavaScript(EXTRACT_TOKEN_SCRIPT);
    }
  }, []);

  const handleMessage = useCallback(async (e: any) => {
    try {
      const data = JSON.parse(e.nativeEvent.data);

      // Look for a JWT-like token in the extracted data
      let token: string | null = data.token ?? null;

      if (!token && data.cookies) {
        // Try cookies: look for any value starting with eyJ
        const parts = data.cookies.split(';');
        for (const p of parts) {
          const v = p.split('=').slice(1).join('=').trim();
          if (v.startsWith('eyJ')) { token = v; break; }
        }
      }

      if (token) {
        await storeToken(token);
        onSuccess(token);
      } else {
        // Show what we received for debugging
        const preview = JSON.stringify(data).slice(0, 200);
        onError(`Logged in but no token found. Received: ${preview}`);
      }
    } catch { /* not our message */ }
  }, [onSuccess, onError]);

  return (
    <Modal visible animationType="slide" onRequestClose={onClose}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Naukri Login</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={styles.closeTxt}>✕ Cancel</Text>
          </TouchableOpacity>
        </View>

        {/* Status bar */}
        <View style={styles.statusBar}>
          <ActivityIndicator size="small" color={C.accentLight} />
          <Text style={styles.statusTxt}>{status}</Text>
        </View>

        {/* WebView — same as Selenium opening the browser */}
        <WebView
          ref={wvRef}
          source={{ uri: LOGIN_URL }}
          style={styles.webView}
          javaScriptEnabled
          domStorageEnabled
          thirdPartyCookiesEnabled
          sharedCookiesEnabled
          onLoadEnd={handleLoadEnd}
          onNavigationStateChange={handleNavigationChange}
          onMessage={handleMessage}
          userAgent="Mozilla/5.0 (Linux; Android 12; Moto G85 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1, backgroundColor: C.bg },
  header:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                paddingHorizontal: 16, paddingVertical: 12,
                backgroundColor: C.card, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:{ fontSize: 16, fontWeight: '700', color: C.text },
  closeBtn:   { padding: 6 },
  closeTxt:   { fontSize: 13, color: C.red, fontWeight: '600' },
  statusBar:  { flexDirection: 'row', alignItems: 'center', gap: 10,
                paddingHorizontal: 16, paddingVertical: 10,
                backgroundColor: C.bgAlt, borderBottomWidth: 1, borderBottomColor: C.border },
  statusTxt:  { fontSize: 12, color: C.textSub, flex: 1 },
  webView:    { flex: 1 },
});
