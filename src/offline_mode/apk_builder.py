"""Build an Android APK from the generated offline HTML guide.

Uses a pre-built Gradle template project (apk-template/) that contains a
minimal WebView activity loading ``file:///android_asset/index.html``.

The build flow:
1. Copy the generated HTML into the template's ``assets/`` folder.
2. Run ``gradlew assembleDebug`` to produce a debug APK.
3. Copy the APK to the requested output path.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

# Resolve the template project directory relative to this file.
# Layout: src/offline_mode/apk_builder.py → ../../apk-template
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "apk-template"


class ApkBuildError(Exception):
    """Raised when the APK build process fails."""


def _find_executable(name: str) -> str | None:
    """Return the full path of *name* if it exists on PATH, else None."""
    return shutil.which(name)


def check_apk_prerequisites() -> list[str]:
    """Verify that the tools required for APK building are available.

    Returns a list of human-readable error strings (empty = all OK).
    """
    errors: list[str] = []

    # JDK
    if not _find_executable("java"):
        errors.append(
            "Java (JDK 17+) is not installed or not on PATH.\n"
            "  Install from https://adoptium.net/ or via your package manager."
        )

    # Android SDK
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not android_home or not Path(android_home).is_dir():
        errors.append(
            "ANDROID_HOME (or ANDROID_SDK_ROOT) environment variable is not set "
            "or points to a missing directory.\n"
            "  Install Android SDK command-line tools from "
            "https://developer.android.com/studio#command-line-tools-only"
        )

    # Template project
    if not _TEMPLATE_DIR.is_dir():
        errors.append(
            f"APK template project not found at {_TEMPLATE_DIR}.\n"
            "  Make sure the apk-template/ directory exists in the repo root."
        )

    return errors


def _gradlew_command() -> str:
    """Return the platform-appropriate gradlew command."""
    if platform.system() == "Windows":
        return str(_TEMPLATE_DIR / "gradlew.bat")
    return str(_TEMPLATE_DIR / "gradlew")


def build_apk(guide_html: str, app_name: str, output_path: str) -> str:
    """Build an APK containing *guide_html* as the offline trip viewer.

    Parameters
    ----------
    guide_html:
        The full HTML string for the offline guide.
    app_name:
        Human-readable trip name (used for the Android app label).
    output_path:
        Destination file path for the built APK.

    Returns
    -------
    str
        The resolved output path where the APK was written.

    Raises
    ------
    ApkBuildError
        If prerequisite checks fail or the Gradle build errors out.
    """
    # --- prerequisite check ---
    errors = check_apk_prerequisites()
    if errors:
        raise ApkBuildError(
            "APK build prerequisites not met:\n\n" + "\n\n".join(errors)
        )

    # --- inject HTML into template assets ---
    assets_dir = _TEMPLATE_DIR / "src" / "main" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    index_html = assets_dir / "index.html"
    index_html.write_text(guide_html, encoding="utf-8")

    # --- update app name in strings.xml ---
    strings_xml = _TEMPLATE_DIR / "src" / "main" / "res" / "values" / "strings.xml"
    strings_xml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        f'    <string name="app_name">{_xml_escape(app_name)}</string>\n'
        "</resources>\n",
        encoding="utf-8",
    )

    # --- run Gradle build ---
    gradlew = _gradlew_command()
    try:
        result = subprocess.run(
            [gradlew, "assembleDebug", "--no-daemon", "-q"],
            cwd=str(_TEMPLATE_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise ApkBuildError(
            f"Gradle wrapper not found at {gradlew}.\n"
            "  Run the build once manually in apk-template/ to bootstrap."
        )
    except subprocess.TimeoutExpired:
        raise ApkBuildError("Gradle build timed out after 5 minutes.")

    if result.returncode != 0:
        raise ApkBuildError(
            f"Gradle build failed (exit code {result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )

    # --- locate and copy APK ---
    apk_path = (
        _TEMPLATE_DIR
        / "build"
        / "outputs"
        / "apk"
        / "debug"
        / "apk-template-debug.apk"
    )
    if not apk_path.exists():
        # Fallback: search for any debug APK
        build_dir = _TEMPLATE_DIR / "build" / "outputs" / "apk" / "debug"
        apks = list(build_dir.glob("*.apk")) if build_dir.exists() else []
        if not apks:
            raise ApkBuildError(
                f"Build succeeded but APK not found in {build_dir}.\n"
                "  Check the Gradle output for details."
            )
        apk_path = apks[0]

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(apk_path), str(output))

    # --- cleanup injected HTML (keep template clean) ---
    index_html.unlink(missing_ok=True)

    return str(output)


def _xml_escape(text: str) -> str:
    """Escape text for safe inclusion in XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
    )
