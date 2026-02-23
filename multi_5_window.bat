@echo off
set MAX_INST=5
for /L %%i in (1,1,%MAX_INST%) do (
    start "Token%%i" cmd /k python modified_script.py
)