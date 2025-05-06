@echo off
echo 백업 시작: %date% %time%

REM 백업할 로컬 저장소 경로
set "local_repo_path=C:\Users\chhwang\PycharmProjects\tradings"
cd /D "%local_repo_path%"

REM 변경 사항 확인
echo 변경 사항 확인...
for /f "delims=" %%a in ('git status -s') do (
    set "changes_exist=true"
    goto :process_changes
)
set "changes_exist="

:process_changes
if not defined changes_exist (
    echo 변경 사항 없음. 백업 생략.
    goto :end
)

echo 모든 .py 및 .bat 파일 스테이징...
git add "*.py"
git add "*.bat"

echo 커밋...
set "timestamp=%date:~0,4%-%date:~5,2%-%date:~8,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%"
git commit -m "자동 백업: %timestamp%"

echo 푸시...
git push origin master
if errorlevel 1 (
    echo 푸시 실패. 오류를 확인하세요.
    pause
    exit /b 1
)
echo 푸시 완료.

:end
echo 백업 완료: %date% %time%
exit /b 0