@echo off
echo ��� ����: %date% %time%

REM ����� ���� ����� ���
set "local_repo_path=C:\Users\chhwang\PycharmProjects\tradings"
cd /D "%local_repo_path%"

REM ���� ���� Ȯ��
echo ���� ���� Ȯ��...
for /f "delims=" %%a in ('git status -s') do (
    set "changes_exist=true"
    goto :process_changes
)
set "changes_exist="

:process_changes
if not defined changes_exist (
    echo ���� ���� ����. ��� ����.
    goto :end
)

echo ��� .py �� .bat ���� ������¡...
git add "*.py"
git add "*.bat"

echo Ŀ��...
set "timestamp=%date:~0,4%-%date:~5,2%-%date:~8,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%"
git commit -m "�ڵ� ���: %timestamp%"

echo Ǫ��...
git push origin master
if errorlevel 1 (
    echo Ǫ�� ����. ������ Ȯ���ϼ���.
    pause
    exit /b 1
)
echo Ǫ�� �Ϸ�.

:end
echo ��� �Ϸ�: %date% %time%
exit /b 0