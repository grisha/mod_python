@echo off
rem Copyright 2004 Apache Software Foundation
rem  
rem  Licensed under the Apache License, Version 2.0 (the "License");
rem  you may not use this file except in compliance with the License.
rem  You may obtain a copy of the License at
rem  
rem      http://www.apache.org/licenses/LICENSE-2.0
rem  
rem  Unless required by applicable law or agreed to in writing, software
rem  distributed under the License is distributed on an "AS IS" BASIS,
rem  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
rem  See the License for the specific language governing permissions and
rem  limitations under the License.
rem  
rem Originally developed by Gregory Trubetskoy.
rem  
rem $Id$
rem
rem This script builds the installer for Windows

rmdir /s /q build
del ..\src\*.obj ..\src\*.lib ..\src\*.exp ..\src\*.res
python setup.py.in bdist_wininst --install-script win32_postinstall.py
upx.exe -9 dist\*.exe || echo UPX is not installed, skipping compression
