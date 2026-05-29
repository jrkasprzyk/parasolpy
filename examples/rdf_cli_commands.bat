@echo off
rem Sample commands demonstrating the parasolpy RDF CLI against the bundled RDF file.
rem Run from anywhere (parasolpy must be installed, e.g. `pip install -e .`):
rem     examples\rdf_cli_commands.bat
rem
rem Reads the bundled sample at parasolpy\data\sample_traces.rdf and writes CSV
rem output into examples\_output\.

setlocal enabledelayedexpansion

set REPO=%~dp0..
set CLI=python -m parasolpy.rdf

set TRACES=%REPO%\parasolpy\data\sample_traces.rdf
set OUTDIR=%~dp0_output
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo ============================================================
echo 1. Info: inspect sample_traces.rdf
echo ============================================================
%CLI% info "%TRACES%"

echo.
echo ============================================================
echo 2. Convert all slots in sample_traces.rdf (wide format)
echo    Scalar slots auto-generate a _labels.csv sidecar per output file.
echo ============================================================
for /f "usebackq delims=" %%S in (`%CLI% slots "%TRACES%" --series-only`) do (
    set "SLOT=%%S"

    rem Build a safe filename: replace spaces and dots with underscores
    set "SAFE=%%S"
    set "SAFE=!SAFE: =_!"
    set "SAFE=!SAFE:.=_!"

    set "OUT=%OUTDIR%\output_!SAFE!_wide.csv"
    echo   slot : !SLOT!
    echo   out  : !OUT!
    %CLI% convert "%TRACES%" --slot "!SLOT!" --output "!OUT!" --format wide
    echo.
)

echo ============================================================
echo 3. Convert all slots in sample_traces.rdf (stacked-header wide format)
echo    Output includes scalar label rows above wide data columns.
echo ============================================================
for /f "usebackq delims=" %%S in (`%CLI% slots "%TRACES%" --series-only`) do (
    set "SLOT=%%S"

    set "SAFE=%%S"
    set "SAFE=!SAFE: =_!"
    set "SAFE=!SAFE:.=_!"

    set "OUT=%OUTDIR%\output_!SAFE!_stacked.csv"
    echo   slot : !SLOT!
    echo   out  : !OUT!
    %CLI% convert "%TRACES%" --slot "!SLOT!" --output "!OUT!" --format stacked
    echo.
)

echo ============================================================
echo 4. Convert all slots in sample_traces.rdf (long format)
echo ============================================================
for /f "usebackq delims=" %%S in (`%CLI% slots "%TRACES%" --series-only`) do (
    set "SLOT=%%S"

    set "SAFE=%%S"
    set "SAFE=!SAFE: =_!"
    set "SAFE=!SAFE:.=_!"

    set "OUT=%OUTDIR%\output_!SAFE!_long.csv"
    echo   slot : !SLOT!
    echo   out  : !OUT!
    %CLI% convert "%TRACES%" --slot "!SLOT!" --output "!OUT!" --format long
    echo.
)

echo Done.

endlocal
