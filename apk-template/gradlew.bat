@rem Gradle wrapper start-up script for Windows

@if "%DEBUG%"=="" @echo off

set DIRNAME=%~dp0
set CLASSPATH=%DIRNAME%gradle\wrapper\gradle-wrapper.jar

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome
set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if %ERRORLEVEL% equ 0 goto execute
echo ERROR: JAVA_HOME is not set and no 'java' command found in PATH. >&2
exit /b 1

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe
if exist "%JAVA_EXE%" goto execute
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME% >&2
exit /b 1

:execute
"%JAVA_EXE%" %JAVA_OPTS% -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*

:end
