import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


APPLICATION_ID = 'com.lumenlink.client'
ABIS = ('armeabi-v7a', 'arm64-v8a', 'x86_64')


def prepare(source, version):
    pubspec = (source / 'pubspec.yaml').read_text()
    if not re.search(rf'^version: {re.escape(version)}\+', pubspec, re.MULTILINE):
        raise ValueError('Source version does not match the requested version')

    gradle = source / 'android/app/build.gradle.kts'
    text = gradle.read_text()
    original = 'applicationId = "com.follow.clash"'
    if text.count(original) != 1:
        raise ValueError('Expected exactly one original application ID')
    text = text.replace(original, f'applicationId = "{APPLICATION_ID}"')

    google_services = source / 'android/app/google-services.json'
    if version == '0.9.0':
        config = json.loads(google_services.read_text())
        client = next(
            client for client in config['client']
            if client['client_info']['android_client_info']['package_name'] == 'com.follow.clash'
        )
        client['client_info']['android_client_info']['package_name'] = APPLICATION_ID
        config['client'] = [client]
        google_services.write_text(json.dumps(config, indent=2) + '\n')
        # A repackaged build has no authority to upload symbols to upstream Firebase.
        text += '\ntasks.matching { it.name.startsWith("uploadCrashlytics") }.configureEach {\n    enabled = false\n}\n'
    gradle.write_text(text)

    names = ('KEYSTORE', 'STORE_PASSWORD', 'KEY_ALIAS', 'KEY_PASSWORD')
    if any(not os.environ.get(name) for name in names):
        raise ValueError('Configure KEYSTORE, STORE_PASSWORD, KEY_ALIAS and KEY_PASSWORD secrets')
    keystore = source / 'android/app/keystore.jks'
    keystore.write_bytes(base64.b64decode(os.environ['KEYSTORE'], validate=True))
    keystore.chmod(0o600)
    properties = source / 'android/local.properties'
    with properties.open('a') as output:
        for property_name, secret in (
            ('storePassword', 'STORE_PASSWORD'),
            ('keyAlias', 'KEY_ALIAS'),
            ('keyPassword', 'KEY_PASSWORD'),
        ):
            value = os.environ[secret]
            value = value.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
            value = value.replace(' ', '\\ ').replace('\t', '\\t')
            output.write(f'\n{property_name}={value}\n')
    properties.chmod(0o600)
    print(f'Prepared Android {version}: {APPLICATION_ID}')


def collect(source, version):
    sdk = Path(os.environ['ANDROID_HOME'])
    build_tools = max(
        (path for path in (sdk / 'build-tools').iterdir() if (path / 'aapt').is_file()),
        key=lambda path: tuple(int(part) for part in re.findall(r'\d+', path.name)),
    )
    destination = Path('dist')
    destination.mkdir(exist_ok=True)
    for abi in ABIS:
        apk = source / f'build/app/outputs/flutter-apk/app-{abi}-release.apk'
        badging = subprocess.check_output([build_tools / 'aapt', 'dump', 'badging', apk], text=True)
        package = badging.splitlines()[0]
        if f"name='{APPLICATION_ID}'" not in package or f"versionName='{version}'" not in package:
            raise ValueError(f'Unexpected APK identity: {package}')
        if f"native-code: '{abi}'" not in badging:
            raise ValueError(f'Unexpected APK architecture: {apk.name}')
        subprocess.run([build_tools / 'apksigner', 'verify', '--verbose', apk], check=True)
        target = destination / f'FlClash-{version}-android-{abi}.apk'
        shutil.copyfile(apk, target)
        print(f'{target.name}: {package}')


def main():
    parser = argparse.ArgumentParser(description='Prepare and verify Android-only release builds')
    parser.add_argument('stage', choices=('prepare', 'collect'))
    parser.add_argument('source', type=Path)
    parser.add_argument('version', choices=('0.9.0', '0.9.2'))
    args = parser.parse_args()
    {'prepare': prepare, 'collect': collect}[args.stage](args.source, args.version)


if __name__ == '__main__':
    main()
