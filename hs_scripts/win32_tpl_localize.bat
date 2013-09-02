set MINGW_BIN=C:\MinGW\bin
set INSTALL32=C:\Program Files (x86)
set CODE=%USERPROFILE%\code

set HS_TPL=%CODE%\hotspotter\tpl
set EXTERN_FEAT=%HS_TPL%\extern_feat

set HESAFF_BIN=%CODE%\hesaff\build
set OPENCV_BIN=%INSTALL32%\OpenCV\bin
::set FLANN_BIN=%INSTALL32%\Flann\bin


cd %EXTERN_FEAT%

:: MinGW Dependencies
for %x in (libstdc++-6.dll, libgcc_s_dw2-1.dll) do ^
copy "%MINGW_BIN%\%x" "%x"

:: OpenCV Dependencies
for %x in (libopencv_core249.dll, libopencv_highgui249.dll, libopencv_imgproc249.dll) do ^
copy "%OPENCV_BIN%\%x" "%x"

:: HessAff Executable 
copy %HESAFF_BIN%\hesaff.exe hesaff.exe

:: Download the others from featurespace.org
