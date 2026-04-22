"""Tests for the APK builder module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wanderlogpro.offline_mode.apk_builder import (
    ApkBuildError,
    _xml_escape,
    build_apk,
    check_apk_prerequisites,
)


class TestCheckApkPrerequisites:
    """Tests for check_apk_prerequisites()."""

    @patch("wanderlogpro.offline_mode.apk_builder._find_executable")
    @patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", Path("/fake/template"))
    def test_missing_java(self, mock_find):
        mock_find.return_value = None
        errors = check_apk_prerequisites()
        assert any("Java" in e for e in errors)

    @patch("wanderlogpro.offline_mode.apk_builder._find_executable", return_value="/usr/bin/java")
    @patch.dict(os.environ, {}, clear=True)
    @patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", Path("/fake/template"))
    def test_missing_android_home(self, mock_find):
        # Remove ANDROID_HOME and ANDROID_SDK_ROOT
        os.environ.pop("ANDROID_HOME", None)
        os.environ.pop("ANDROID_SDK_ROOT", None)
        errors = check_apk_prerequisites()
        assert any("ANDROID_HOME" in e for e in errors)

    @patch("wanderlogpro.offline_mode.apk_builder._find_executable", return_value="/usr/bin/java")
    @patch.dict(os.environ, {"ANDROID_HOME": "/fake/sdk"}, clear=True)
    @patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", Path("/fake/template"))
    def test_missing_template_dir(self, mock_find):
        errors = check_apk_prerequisites()
        assert any("template" in e.lower() for e in errors)

    @patch("wanderlogpro.offline_mode.apk_builder._find_executable", return_value="/usr/bin/java")
    @patch.dict(os.environ, {"ANDROID_HOME": "."}, clear=True)
    @patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", Path("."))
    def test_all_present(self, mock_find):
        errors = check_apk_prerequisites()
        # Only template dir check should pass since "." exists
        assert not any("Java" in e for e in errors)
        assert not any("ANDROID_HOME" in e for e in errors)


class TestXmlEscape:
    """Tests for the XML escape helper."""

    def test_escapes_special_chars(self):
        assert _xml_escape('Trip & "Fun" <2026>') == "Trip &amp; &quot;Fun&quot; &lt;2026&gt;"

    def test_plain_text_unchanged(self):
        assert _xml_escape("My Trip") == "My Trip"

    def test_apostrophe(self):
        assert _xml_escape("It's great") == "It&apos;s great"


class TestBuildApk:
    """Tests for the build_apk() function."""

    @patch("wanderlogpro.offline_mode.apk_builder.check_apk_prerequisites")
    def test_raises_on_failed_prerequisites(self, mock_check):
        mock_check.return_value = ["Java not found"]
        with pytest.raises(ApkBuildError, match="prerequisites not met"):
            build_apk("<html></html>", "Test Trip", "out.apk")

    @patch("wanderlogpro.offline_mode.apk_builder.check_apk_prerequisites", return_value=[])
    @patch("wanderlogpro.offline_mode.apk_builder.subprocess.run")
    def test_raises_on_gradle_failure(self, mock_run, mock_check, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stderr="BUILD FAILED", stdout="")

        with patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", tmp_path):
            # Create the assets and res directories the function expects
            (tmp_path / "src" / "main" / "assets").mkdir(parents=True)
            (tmp_path / "src" / "main" / "res" / "values").mkdir(parents=True)

            with pytest.raises(ApkBuildError, match="Gradle build failed"):
                build_apk("<html></html>", "Test Trip", str(tmp_path / "out.apk"))

    @patch("wanderlogpro.offline_mode.apk_builder.check_apk_prerequisites", return_value=[])
    @patch("wanderlogpro.offline_mode.apk_builder.subprocess.run")
    def test_raises_on_timeout(self, mock_run, mock_check, tmp_path):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gradlew", timeout=300)

        with patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", tmp_path):
            (tmp_path / "src" / "main" / "assets").mkdir(parents=True)
            (tmp_path / "src" / "main" / "res" / "values").mkdir(parents=True)

            with pytest.raises(ApkBuildError, match="timed out"):
                build_apk("<html></html>", "Test Trip", str(tmp_path / "out.apk"))

    @patch("wanderlogpro.offline_mode.apk_builder.check_apk_prerequisites", return_value=[])
    @patch("wanderlogpro.offline_mode.apk_builder.subprocess.run")
    def test_successful_build(self, mock_run, mock_check, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        with patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", tmp_path):
            # Set up directory structure
            assets_dir = tmp_path / "src" / "main" / "assets"
            assets_dir.mkdir(parents=True)
            res_dir = tmp_path / "src" / "main" / "res" / "values"
            res_dir.mkdir(parents=True)

            # Create a fake APK output
            apk_dir = tmp_path / "build" / "outputs" / "apk" / "debug"
            apk_dir.mkdir(parents=True)
            fake_apk = apk_dir / "apk-template-debug.apk"
            fake_apk.write_bytes(b"PK\x03\x04fake-apk")

            output = str(tmp_path / "my-trip.apk")
            result = build_apk("<html>hello</html>", "My Trip", output)

            assert Path(result).exists()
            assert Path(result).read_bytes() == b"PK\x03\x04fake-apk"

            # Verify HTML was injected then cleaned up
            assert not (assets_dir / "index.html").exists()

            # Verify strings.xml was updated
            strings_content = (res_dir / "strings.xml").read_text()
            assert "My Trip" in strings_content

    @patch("wanderlogpro.offline_mode.apk_builder.check_apk_prerequisites", return_value=[])
    @patch("wanderlogpro.offline_mode.apk_builder.subprocess.run")
    def test_xml_escaping_in_app_name(self, mock_run, mock_check, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)

        with patch("wanderlogpro.offline_mode.apk_builder._TEMPLATE_DIR", tmp_path):
            assets_dir = tmp_path / "src" / "main" / "assets"
            assets_dir.mkdir(parents=True)
            res_dir = tmp_path / "src" / "main" / "res" / "values"
            res_dir.mkdir(parents=True)
            apk_dir = tmp_path / "build" / "outputs" / "apk" / "debug"
            apk_dir.mkdir(parents=True)
            (apk_dir / "apk-template-debug.apk").write_bytes(b"PK")

            build_apk("<html></html>", 'Trip "Fun" & <More>', str(tmp_path / "out.apk"))

            strings = (res_dir / "strings.xml").read_text()
            assert "&amp;" in strings
            assert "&quot;" in strings
            assert "&lt;" in strings
