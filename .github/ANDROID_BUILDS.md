# Android APK builds

Run **Android APK** from the Actions tab. Each run checks out the original
`v0.9.0` and `v0.9.2` tags and builds only Android release APKs. Changes to
the workflow or its preparation script on `main` also start a run.

Both versions use the application ID `com.lumenlink.client`. Kotlin namespaces
and Flutter channel names retain their original values so existing native
components keep working. The renamed app installs separately from upstream.

Each version publishes these individual APK assets to its matching GitHub
Release (`v0.9.0` or `v0.9.2`):

- `FlClash-<version>-android-arm64-v8a.apk`
- `FlClash-<version>-android-armeabi-v7a.apk`
- `FlClash-<version>-android-x86_64.apk`

Before publishing, the workflow verifies the application ID, version name, ABI
and APK signature. It uploads no ZIP artifacts to Actions and saves no build
caches. No desktop packages, website deployment or external release
notifications run in this workflow.

Configure these repository Actions secrets once, keeping the same signing key
for both versions and future updates:

| Secret | Value |
| --- | --- |
| `KEYSTORE` | Base64-encoded JKS or PKCS12 release keystore |
| `STORE_PASSWORD` | Keystore password |
| `KEY_ALIAS` | Signing key alias |
| `KEY_PASSWORD` | Signing key password |

The build fails if signing credentials are missing. The v0.9.0 Firebase client
configuration is adapted to the new application ID, and its build-time symbol
and mapping uploads are disabled.
